import fs from 'node:fs';
import crypto from 'node:crypto';
const registry=JSON.parse(fs.readFileSync('incumbent-registry.json','utf8'));
const sha=x=>'sha256:'+crypto.createHash('sha256').update(String(x)).digest('hex');
function validIdentity(x){
  return !!x&&typeof x==='object'&&registry.requiredIdentity.every(k=>x[k]!==undefined&&x[k]!==null&&x[k]!=='');
}
export function evaluateReplacementProposal({domain,challengerResult,challengerIdentity}){
  const slot=registry.domains?.[domain]; const incumbent=slot?.active;
  const reasons=[];
  if(!slot) reasons.push('DOMAIN_NOT_REGISTERED');
  if(slot?.status!=='VERIFIED'||!validIdentity(incumbent)) reasons.push('INCUMBENT_NOT_VERIFIED');
  if(!validIdentity(challengerIdentity)) reasons.push('CHALLENGER_IDENTITY_INVALID');
  if(challengerIdentity?.zeroSpendVerified!==true) reasons.push('CHALLENGER_ZERO_SPEND_NOT_PROVEN');
  if(!challengerResult||challengerResult.grade!=='replacementGrade') reasons.push('REPLACEMENT_GRADE_REQUIRED');
  if(!['REPLACEMENT_CANDIDATE','NON_INFERIOR_CANDIDATE'].includes(challengerResult?.decision)) reasons.push('CHALLENGER_DECISION_INSUFFICIENT');
  if(challengerResult?.gates?.sampleOk!==true||challengerResult?.gates?.pairedOk!==true||challengerResult?.gates?.integrityOk!==true) reasons.push('CHALLENGER_GATES_INCOMPLETE');
  if(challengerResult?.replacementApplied!==false) reasons.push('AUTOMATIC_REPLACEMENT_FORBIDDEN');
  const approved=reasons.length===0;
  return {schema:'arbm-replacement-proposal-gate-v1',approved,action:approved?'OPEN_P9_REPLACEMENT_PROPOSAL':'BLOCK',domain,reasons,incumbentIdentity:incumbent||null,challengerIdentity:challengerIdentity||null,proposalHash:sha(JSON.stringify({domain,incumbent,challengerIdentity,challengerResult}))};
}
