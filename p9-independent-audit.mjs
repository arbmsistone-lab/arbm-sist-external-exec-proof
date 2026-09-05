import crypto from 'node:crypto';
import fs from 'node:fs';
import { REQUIRED_DIMENSIONS } from './codex-parity-gate.mjs';

const sha256=x=>crypto.createHash('sha256').update(x).digest('hex');
const finite01=x=>Number.isFinite(Number(x))&&Number(x)>=0&&Number(x)<=1;
function mean(xs){return xs.reduce((a,b)=>a+b,0)/xs.length;}
function pairedCiLowerPp(diffs,z=1.96){
  const n=diffs.length,m=mean(diffs);
  if(n<2)return m*100;
  const variance=diffs.reduce((s,x)=>s+(x-m)**2,0)/(n-1);
  return (m-z*Math.sqrt(variance/n))*100;
}
export function auditParitySamples(input={}){
  const reasons=[],rows=Array.isArray(input.samples)?input.samples:[];
  if(input.schema!=='arbm-p9-paired-samples-v1')reasons.push('AUDIT_SCHEMA_INVALID');
  if(input.independentAuditor!==true)reasons.push('INDEPENDENT_AUDITOR_NOT_PROVEN');
  if(input.sameTaskContract!==true)reasons.push('SAME_TASK_CONTRACT_NOT_PROVEN');
  const dimensions=[];
  for(const id of REQUIRED_DIMENSIONS){
    const group=rows.filter(r=>r?.dimension===id);
    if(group.length<30){reasons.push(`INSUFFICIENT_PAIRED_SAMPLES:${id}`);continue;}
    if(group.some(r=>!finite01(r.arbm)||!finite01(r.codex))){reasons.push(`INVALID_SAMPLE_SCORE:${id}`);continue;}
    const taskIds=group.map(r=>String(r.taskId||''));
    if(taskIds.some(x=>!x)||new Set(taskIds).size!==taskIds.length){reasons.push(`TASK_ID_INVALID:${id}`);continue;}
    const arbm=mean(group.map(r=>Number(r.arbm))),codex=mean(group.map(r=>Number(r.codex)));
    const diffs=group.map(r=>Number(r.arbm)-Number(r.codex));
    const raw=Buffer.from(JSON.stringify(group));
    dimensions.push({id,arbm,codex,samples:group.length,ciLowerDifferencePp:pairedCiLowerPp(diffs),artifactSha256:[sha256(raw)]});
  }
  const pass=reasons.length===0&&dimensions.length===REQUIRED_DIMENSIONS.length;
  return {schema:'arbm-p9-independent-audit-v1',pass,reasons,dimensions,inputSha256:sha256(Buffer.from(JSON.stringify(input)))};
}

export function mergeAuditIntoEvidence(evidence,audit){
  if(!audit?.pass)throw new Error('independent_audit_not_passed');
  return {...evidence,status:'AUDITED',p9IndependentAudit:true,dimensions:audit.dimensions,p9Audit:{schema:audit.schema,inputSha256:audit.inputSha256}};
}

if(process.argv[1]?.endsWith('p9-independent-audit.mjs')){
  const [inputFile,evidenceFile,outFile]=process.argv.slice(2);if(!inputFile||!evidenceFile||!outFile)process.exit(64);
  try{const input=JSON.parse(fs.readFileSync(inputFile,'utf8')),evidence=JSON.parse(fs.readFileSync(evidenceFile,'utf8'));const audit=auditParitySamples(input);if(!audit.pass){console.log(JSON.stringify(audit,null,2));process.exit(2);}const merged=mergeAuditIntoEvidence(evidence,audit);fs.writeFileSync(outFile,JSON.stringify(merged,null,2)+'\n');console.log(JSON.stringify(audit,null,2));}
  catch(error){console.error(JSON.stringify({pass:false,error:String(error?.message||error)}));process.exit(65);}
}
