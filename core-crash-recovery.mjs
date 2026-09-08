import fs from 'node:fs';
import {appendEvidence,verifyLedger,findEvidence} from './universal-radar-evidence-ledger.mjs';
const regPath='incumbent-registry.json';
const queuePath='replacement-proposals.json';
const ledgerPath='universal-radar-evidence-ledger.jsonl';
const loadJson=(p,fallback)=>fs.existsSync(p)?JSON.parse(fs.readFileSync(p,'utf8')):fallback;
const entries=()=>fs.existsSync(ledgerPath)?fs.readFileSync(ledgerPath,'utf8').split(/\r?\n/).filter(Boolean).map(JSON.parse):[];
const hasEvent=(type,field,value)=>entries().some(e=>e.payload?.type===type&&e.payload?.[field]===value);
function certValid(hash,proposalHash,domain,artifact){
 const e=findEvidence(hash),p=e?.entry?.payload;
 return e.ok&&p?.type==='REPLACEMENT_CERTIFIED'&&p?.status==='PASS'&&p?.rollbackReady===true&&p?.proposalHash===proposalHash&&p?.domain===domain&&p?.challengerArtifactSha256===artifact;
}
function rollbackValid(hash,promotionHash,domain){
 const e=findEvidence(hash),p=e?.entry?.payload;
 return e.ok&&p?.type==='ROLLBACK_VALIDATED'&&p?.status==='PASS'&&p?.promotionHash===promotionHash&&p?.domain===domain;
}export function recoverCoreConsistency(){
 const ledger=verifyLedger(); if(!ledger.ok) return {ok:false,recovered:0,reasons:['EVIDENCE_LEDGER_INVALID']};
 const reg=loadJson(regPath,{domains:{}}),q=loadJson(queuePath,{items:[]}); let recovered=0; const reasons=[];
 for(const [domain,slot] of Object.entries(reg.domains||{})) for(const h of slot.history||[]){
  if(h.type==='PROMOTION'&&!hasEvent('INCUMBENT_PROMOTED','promotionHash',h.promotionHash)){
   const laterRollback=(slot.history||[]).some(x=>x.type==='ROLLBACK'&&x.promotionHash===h.promotionHash);
   if((slot.active?.artifactSha256!==h.next?.artifactSha256&&!laterRollback)||!certValid(h.evidenceHash,h.proposalHash,domain,h.next?.artifactSha256)){reasons.push('PROMOTION_RECOVERY_UNPROVEN:'+h.promotionHash);continue;}
   appendEvidence({type:'INCUMBENT_PROMOTED',domain,promotionHash:h.promotionHash,proposalHash:h.proposalHash,evidenceHash:h.evidenceHash,recoveredAfterCrash:true}); recovered++;
  }
  if(h.type==='ROLLBACK'&&!hasEvent('INCUMBENT_ROLLED_BACK','rollbackHash',h.rollbackHash)){
   if(slot.active?.artifactSha256!==h.restored?.artifactSha256||!rollbackValid(h.evidenceHash,h.promotionHash,domain)){reasons.push('ROLLBACK_RECOVERY_UNPROVEN:'+h.rollbackHash);continue;}
   appendEvidence({type:'INCUMBENT_ROLLED_BACK',domain,rollbackHash:h.rollbackHash,promotionHash:h.promotionHash,proposalHash:(slot.history||[]).find(x=>x.promotionHash===h.promotionHash)?.proposalHash,reason:h.reason,evidenceHash:h.evidenceHash,recoveredAfterCrash:true}); recovered++;
  }
 }
 for(const item of q.items||[]){
  if(item.status==='PENDING_P9'&&!hasEvent('REPLACEMENT_PROPOSAL','proposalHash',item.proposalHash)) reasons.push('QUEUE_ORPHAN_NO_LEDGER:'+item.proposalHash);
 }
 return {ok:reasons.length===0,recovered,reasons};
}