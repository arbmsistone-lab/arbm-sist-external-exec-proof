import fs from 'node:fs';
import crypto from 'node:crypto';
const workflowPath='.github/workflows/p8-swe-rebench-smoke.yml';
const sha=v=>'sha256:'+crypto.createHash('sha256').update(String(v)).digest('hex');
const read=path=>fs.existsSync(path)?fs.readFileSync(path,'utf8'):'';
function envValue(yaml,key){
  const re=new RegExp(`^\\s*${key}:\\s*['\"]?([^'\"\\r\\n]+)['\"]?\\s*$`,'m');
  return yaml.match(re)?.[1]?.trim()||null;
}
export function discoverIncumbents(){
  const yaml=read(workflowPath); const configHash=yaml?sha(yaml):null;
  const defs=[
    ['quality-cost','ARBM_BENCHMARK_QUALITY_ENDPOINT','PAID_OR_COST_ROUTE'],
    ['free-primary','ARBM_BENCHMARK_ENDPOINT','FREE_CANDIDATE_ROUTE'],
    ['free-fallback','ARBM_BENCHMARK_FALLBACK_ENDPOINT','FREE_CANDIDATE_ROUTE'],
    ['sovereign','ARBM_SOVEREIGN_ENDPOINT','SOVEREIGN_ROUTE']
  ];
  const routes=defs.map(([id,key,kind])=>({
    id,key,kind,endpoint:envValue(yaml,key),configured:Boolean(envValue(yaml,key)),
    configSource:workflowPath,configHash
  }));
  const evidencePaths=['p8-swe-artifact/agent-evidence.json','evidence/agent-evidence.json'];
  const evidencePath=evidencePaths.find(fs.existsSync)||null;
  let evidence=null;
  if(evidencePath){try{evidence=JSON.parse(read(evidencePath));}catch{evidence={parseError:true};}}
  return {
    schema:'arbm-incumbent-discovery-v1',
    observedAt:new Date().toISOString(),
    routes,
    evidencePath,
    evidence
  };
}
export function runtimeRouteFromEvidence(evidence){
  const ledger=Array.isArray(evidence?.providerCallLedger)?evidence.providerCallLedger:[];
  const ok=ledger.filter(x=>x?.status==='ok');
  if(!ok.length) return null;
  const last=ok[ok.length-1];
  const observed=evidence?.observedAt||null; const generated=evidence?.generatedAt||null;
  const timestampAmbiguous=Boolean(observed&&generated&&observed!==generated);
  return {
    route:String(last.route||''),
    model:last.model||null,
    pipeline:last.pipeline||null,
    providerCostUsd:last.costUsd===null||last.costUsd===undefined?null:Number(last.costUsd),
    sourceCommit:evidence?.sourceCommit||null,
    modelArtifactSha256:evidence?.modelArtifactSha256||null,
    observedAt:timestampAmbiguous?null:(observed||generated),timestampAmbiguous,
    validPatch:evidence?.validPatch===true,
    status:evidence?.status||null
  };
}
