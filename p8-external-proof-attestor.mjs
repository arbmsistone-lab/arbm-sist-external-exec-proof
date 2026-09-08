import fs from 'node:fs';
import crypto from 'node:crypto';
import {discoverIncumbents} from './incumbent-discovery.mjs';
import {attestDiscovery} from './incumbent-attestor.mjs';
const sha=v=>'sha256:'+crypto.createHash('sha256').update(String(v)).digest('hex');
const hex64=x=>/^[0-9a-f]{64}$/i.test(String(x||''));
export function attestationFromEnvelope(path='p8-external-proof-envelope.json'){
  const e=JSON.parse(fs.readFileSync(path,'utf8'));
  const bad=[];
  if(e.schema!=='arbm-p8-external-proof-envelope-v1') bad.push('BAD_SCHEMA');
  if(e.workflowConclusion!=='success'||e.validPatch!==true||e.officialEvaluatorAllOk!==true) bad.push('EXECUTION_NOT_PROVEN');
  if(e.zeroSpendMode!=='HARD'||Number(e.providerCostUsd)!==0) bad.push('ZERO_SPEND_NOT_PROVEN');
  if(e.actualRoute!=='free-primary'||!e.actualPipeline) bad.push('RUNTIME_IDENTITY_INCOMPLETE');
  if(!String(e.artifactDigest||'').startsWith('sha256:')||!hex64(e.agentEvidenceSha256)||!hex64(e.evalReportSha256)||!hex64(e.patchesSha256)) bad.push('HASH_EVIDENCE_INCOMPLETE');
  if(!e.sourceCommit||!e.artifactCreatedAt) bad.push('PROVENANCE_INCOMPLETE');
  if(bad.length) throw new Error('P8_EXTERNAL_PROOF_INVALID:'+bad.join(','));
  const d=discoverIncumbents();
  d.evidence={sourceCommit:e.sourceCommit,observedAt:e.artifactCreatedAt,providerCostUsd:0,validPatch:true,status:'',modelArtifactSha256:sha(e.artifactDigest),providerCallLedger:[{route:e.actualRoute,status:'ok',model:null,pipeline:e.actualPipeline,costUsd:0}]};
  return attestDiscovery(d,new Date(e.artifactCreatedAt));
}
