import fs from 'node:fs';
import crypto from 'node:crypto';
import {appendEvidence,verifyLedger} from './universal-radar-evidence-ledger.mjs';
const path='incumbent-registry.json';
const sha=x=>'sha256:'+crypto.createHash('sha256').update(String(x)).digest('hex');
const digest=x=>/^sha256:[0-9a-f]{64}$/i.test(String(x||''));
const validTime=x=>Number.isFinite(Date.parse(String(x||'')));
const validIdentity=x=>!!x&&typeof x==='object'&&['id','version','artifactSha256','activatedAt','zeroSpendVerified'].every(k=>x[k]!==undefined&&x[k]!==null&&x[k]!=='')&&digest(x.artifactSha256)&&validTime(x.activatedAt)&&x.zeroSpendVerified===true;
const stable=x=>JSON.stringify(x,Object.keys(x||{}).sort());
function atomicWrite(reg){const tmp=path+'.tmp-'+process.pid;const fd=fs.openSync(tmp,'w');try{fs.writeFileSync(fd,JSON.stringify(reg,null,2));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(tmp,path);}
const load=()=>JSON.parse(fs.readFileSync(path,'utf8'));
export function promoteReplacement({domain,proposal,challengerIdentity,certification}){
  const reg=load(); const slot=reg.domains?.[domain]; const reasons=[];
  if(!slot) reasons.push('DOMAIN_NOT_REGISTERED');
  if(slot?.status!=='VERIFIED'||!validIdentity(slot?.active)) reasons.push('INCUMBENT_NOT_VERIFIED');
  if(proposal?.approved!==true||proposal?.action!=='OPEN_P9_REPLACEMENT_PROPOSAL'||!digest(proposal?.proposalHash)) reasons.push('PROPOSAL_NOT_APPROVED');
  if(stable(proposal?.incumbentIdentity)!==stable(slot?.active)) reasons.push('INCUMBENT_CHANGED_SINCE_PROPOSAL');
  if(!validIdentity(challengerIdentity)) reasons.push('CHALLENGER_IDENTITY_INVALID');
  if(stable(proposal?.challengerIdentity)!==stable(challengerIdentity)) reasons.push('CHALLENGER_IDENTITY_MISMATCH');
  if(certification?.status!=='PASS'||certification?.rollbackReady!==true||!digest(certification?.evidenceHash)) reasons.push('CERTIFICATION_INCOMPLETE');
  const ledgerCheck=verifyLedger(); if(!ledgerCheck.ok) reasons.push('EVIDENCE_LEDGER_INVALID');
  if(reasons.length) return {schema:'arbm-incumbent-promotion-v1',promoted:false,reasons};
  const original=structuredClone(reg); const previous=structuredClone(slot.active); const now=new Date().toISOString();
  const promotionHash=sha(JSON.stringify({domain,previous,challengerIdentity,proposalHash:proposal.proposalHash,evidenceHash:certification.evidenceHash,now}));
  slot.history=Array.isArray(slot.history)?slot.history:[];
  slot.history.push({type:'PROMOTION',at:now,promotionHash,previous,next:challengerIdentity,proposalHash:proposal.proposalHash,evidenceHash:certification.evidenceHash});
  slot.history=slot.history.slice(-100); slot.active=challengerIdentity; slot.status='VERIFIED'; slot.verifiedAt=now; slot.usableForReplacementProposal=true; slot.lastPromotionHash=promotionHash; reg.updatedAt=now;
  atomicWrite(reg); let ev; try{ev=appendEvidence({type:'INCUMBENT_PROMOTED',domain,promotionHash,proposalHash:proposal.proposalHash,evidenceHash:certification.evidenceHash});}catch(e){atomicWrite(original);throw e;}
  return {schema:'arbm-incumbent-promotion-v1',promoted:true,domain,promotionHash,previous,active:challengerIdentity,evidenceHash:ev.entryHash};
}
export function rollbackReplacement({domain,promotionHash,reason,evidenceHash}){
  const reg=load(); const slot=reg.domains?.[domain]; const reasons=[]; const history=slot?.history||[]; const promotion=[...history].reverse().find(x=>x.type==='PROMOTION'&&x.promotionHash===promotionHash);
  if(!slot) reasons.push('DOMAIN_NOT_REGISTERED');
  if(!promotion) reasons.push('PROMOTION_NOT_FOUND');
  if(slot?.lastPromotionHash!==promotionHash) reasons.push('PROMOTION_NOT_CURRENT');
  if(!validIdentity(promotion?.previous)) reasons.push('ROLLBACK_TARGET_INVALID');
  if(!String(reason||'').trim()) reasons.push('ROLLBACK_REASON_REQUIRED');
  if(!digest(evidenceHash)) reasons.push('ROLLBACK_EVIDENCE_INVALID');
  const ledgerCheck=verifyLedger(); if(!ledgerCheck.ok) reasons.push('EVIDENCE_LEDGER_INVALID');
  if(reasons.length) return {schema:'arbm-incumbent-rollback-v1',rolledBack:false,reasons};
  const original=structuredClone(reg); const now=new Date().toISOString(); const failed=structuredClone(slot.active); const rollbackHash=sha(JSON.stringify({domain,promotionHash,failed,restored:promotion.previous,reason,evidenceHash,now}));
  slot.active=promotion.previous; slot.status='VERIFIED'; slot.verifiedAt=now; slot.usableForReplacementProposal=true; slot.lastRollbackHash=rollbackHash; slot.lastPromotionHash=null;
  slot.history.push({type:'ROLLBACK',at:now,rollbackHash,promotionHash,failed,restored:promotion.previous,reason,evidenceHash}); slot.history=slot.history.slice(-100); reg.updatedAt=now;
  atomicWrite(reg); let ev; try{ev=appendEvidence({type:'INCUMBENT_ROLLED_BACK',domain,rollbackHash,promotionHash,reason,evidenceHash});}catch(e){atomicWrite(original);throw e;}
  return {schema:'arbm-incumbent-rollback-v1',rolledBack:true,domain,rollbackHash,failed,active:promotion.previous,evidenceHash:ev.entryHash};
}
