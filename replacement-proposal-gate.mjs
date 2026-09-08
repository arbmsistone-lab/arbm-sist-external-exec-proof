import fs from 'node:fs';
import crypto from 'node:crypto';
const loadRegistry=()=>JSON.parse(fs.readFileSync('incumbent-registry.json','utf8'));
const sha=x=>'sha256:'+crypto.createHash('sha256').update(String(x)).digest('hex');
const digest=x=>/^sha256:[0-9a-f]{64}$/i.test(String(x||''));
const validTime=x=>Number.isFinite(Date.parse(String(x||'')));
function validIdentity(x,requiredIdentity){
  return !!x&&typeof x==='object'&&requiredIdentity.every(k=>x[k]!==undefined&&x[k]!==null&&x[k]!=='')&&digest(x.artifactSha256)&&validTime(x.activatedAt)&&x.zeroSpendVerified===true;
}

export function evaluateReplacementProposal({domain,challengerResult,challengerIdentity}){
  const registry=loadRegistry(); const slot=registry.domains?.[domain]; const incumbent=slot?.active;
  const reasons=[];
  if(!slot) reasons.push('DOMAIN_NOT_REGISTERED');
  if(slot?.status!=='VERIFIED'||!validIdentity(incumbent,registry.requiredIdentity)) reasons.push('INCUMBENT_NOT_VERIFIED');
  if(!validIdentity(challengerIdentity,registry.requiredIdentity)) reasons.push('CHALLENGER_IDENTITY_INVALID');
  if(challengerIdentity?.zeroSpendVerified!==true) reasons.push('CHALLENGER_ZERO_SPEND_NOT_PROVEN');
  if(!challengerResult||challengerResult.grade!=='replacementGrade') reasons.push('REPLACEMENT_GRADE_REQUIRED');
  if(!['REPLACEMENT_CANDIDATE','NON_INFERIOR_CANDIDATE'].includes(challengerResult?.decision)) reasons.push('CHALLENGER_DECISION_INSUFFICIENT');
  if(challengerResult?.gates?.sampleOk!==true||challengerResult?.gates?.pairedOk!==true||challengerResult?.gates?.integrityOk!==true) reasons.push('CHALLENGER_GATES_INCOMPLETE');
  if(challengerResult?.replacementApplied!==false) reasons.push('AUTOMATIC_REPLACEMENT_FORBIDDEN');
  const approved=reasons.length===0;
  return {schema:'arbm-replacement-proposal-gate-v1',approved,action:approved?'OPEN_P9_REPLACEMENT_PROPOSAL':'BLOCK',domain,reasons,incumbentIdentity:incumbent||null,challengerIdentity:challengerIdentity||null,proposalHash:sha(JSON.stringify({domain,incumbent,challengerIdentity,challengerResult}))};
}
