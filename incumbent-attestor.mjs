import fs from 'node:fs';
import crypto from 'node:crypto';
import {runtimeRouteFromEvidence} from './incumbent-discovery.mjs';
const policy=JSON.parse(fs.readFileSync('incumbent-attestation-policy.json','utf8'));
const constitution=JSON.parse(fs.readFileSync('arbm-constitution.json','utf8'));
const sha=v=>'sha256:'+crypto.createHash('sha256').update(String(v)).digest('hex');
const known=x=>x!==null&&x!==undefined&&String(x).trim()!==''&&String(x).toLowerCase()!=='unknown';
function ageHours(ts,now){
  if(!known(ts)||Number.isNaN(Date.parse(ts))) return Infinity;
  return Math.max(0,(now.getTime()-Date.parse(ts))/3600000);
}
export function attestDiscovery(discovery,now=new Date()){
  const runtime=runtimeRouteFromEvidence(discovery?.evidence);
  const routes=(discovery?.routes||[]).map(route=>{
    const active=runtime?.route===route.id;
    const hardBlocked=policy.mode.includes('ZERO_SPEND_HARD')&&route.kind==='PAID_OR_COST_ROUTE';
    let state=route.configured?'CONFIGURED_UNATTESTED':'UNVERIFIED';
    const reasons=[];
    if(!route.configured) reasons.push('ROUTE_NOT_CONFIGURED');
    if(hardBlocked) reasons.push('PAID_ROUTE_FORBIDDEN_IN_HARD_MODE');
    if(route.configured&&!active) reasons.push('NO_SUCCESSFUL_EXECUTION_EVIDENCE');
    if(active){
      if(runtime.validPatch!==true) reasons.push('SUCCESS_NOT_PROVEN');
      if(runtime.timestampAmbiguous) reasons.push('EVIDENCE_TIMESTAMP_AMBIGUOUS');
      if(constitution.automaticBilling!==false||constitution.automaticOverage!==false) reasons.push('HARD_COST_GUARD_NOT_ENFORCED');
      if(!known(runtime.pipeline)||!known(runtime.sourceCommit)) reasons.push('RUNTIME_IDENTITY_INCOMPLETE');
      const aggregateCost=discovery?.evidence?.providerCostUsd;
      const zeroCost=runtime.providerCostUsd!==null&&runtime.providerCostUsd!==undefined&&aggregateCost!==null&&aggregateCost!==undefined&&Number(runtime.providerCostUsd)===0&&Number(aggregateCost)===0;
      if(aggregateCost===null||aggregateCost===undefined) reasons.push('AGGREGATE_COST_MISSING');
      if(runtime.providerCostUsd===null||runtime.providerCostUsd===undefined) reasons.push('ROUTE_COST_MISSING');
      if(!zeroCost) reasons.push('ZERO_SPEND_NOT_PROVEN');
      const fresh=ageHours(runtime.observedAt,now)<=Number(policy.maxEvidenceAgeHours||72);
      if(!known(runtime.observedAt)) reasons.push('OBSERVED_AT_MISSING');
      else if(!fresh){state='ATTESTED_STALE';reasons.push('EVIDENCE_STALE');}
      const identityOk=known(runtime.pipeline)&&known(runtime.sourceCommit);
      const successOk=runtime.validPatch===true&&!runtime.timestampAmbiguous&&constitution.automaticBilling===false&&constitution.automaticOverage===false;
      if(!hardBlocked&&identityOk&&zeroCost&&fresh&&known(runtime.observedAt)&&successOk) state='VERIFIED';
    }
    const generatedIdentityDigest=active?sha(JSON.stringify({route:runtime.route,model:runtime.model,pipeline:runtime.pipeline,sourceCommit:runtime.sourceCommit})):null;
    const proofArtifactDigest=active&&runtime.modelArtifactSha256&&runtime.modelArtifactSha256!=='unknown'?runtime.modelArtifactSha256:null;
    const identity=active?{
      id:runtime.route,version:runtime.model||runtime.pipeline,
      artifactSha256:proofArtifactDigest||generatedIdentityDigest,proofArtifactDigest,identityDigest:generatedIdentityDigest,
      activatedAt:runtime.observedAt,zeroSpendVerified:Number(runtime.providerCostUsd)===0,
      model:runtime.model,pipeline:runtime.pipeline,sourceCommit:runtime.sourceCommit
    }:null;
    return {...route,activeEvidence:active,state,reasons,identity};
  });
  const verified=routes.filter(x=>x.state==='VERIFIED');
  return {
    schema:'arbm-incumbent-attestation-v1',observedAt:now.toISOString(),
    verifiedCount:verified.length,configuredCount:routes.filter(x=>x.configured).length,
    replacementSafe:verified.length===1,routes,
    attestationHash:sha(JSON.stringify(routes.map(x=>({id:x.id,state:x.state,identity:x.identity,reasons:x.reasons}))))
  };
}
