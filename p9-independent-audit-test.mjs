import assert from 'node:assert/strict';
import { REQUIRED_DIMENSIONS } from './codex-parity-gate.mjs';
import { auditParitySamples,mergeAuditIntoEvidence } from './p9-independent-audit.mjs';

const samples=[];
for(const dimension of REQUIRED_DIMENSIONS){
  for(let i=0;i<30;i++)samples.push({dimension,taskId:`${dimension}-${i}`,arbm:0.9,codex:0.89});
}
const good={schema:'arbm-p9-paired-samples-v1',independentAuditor:true,sameTaskContract:true,samples};
const audit=auditParitySamples(good);
assert.equal(audit.pass,true);assert.equal(audit.dimensions.length,10);
assert.ok(audit.dimensions.every(x=>x.samples===30&&x.ciLowerDifferencePp>=-2));
const merged=mergeAuditIntoEvidence({status:'BLOCKED_UNVERIFIED',p9IndependentAudit:false,dimensions:[]},audit);
assert.equal(merged.p9IndependentAudit,true);assert.equal(merged.dimensions.length,10);

const short=structuredClone(good);short.samples=short.samples.filter((_,i)=>i!==0);
assert.equal(auditParitySamples(short).pass,false);
const nonIndependent=structuredClone(good);nonIndependent.independentAuditor=false;
assert.ok(auditParitySamples(nonIndependent).reasons.includes('INDEPENDENT_AUDITOR_NOT_PROVEN'));
const duplicate=structuredClone(good);duplicate.samples[1].taskId=duplicate.samples[0].taskId;
assert.equal(auditParitySamples(duplicate).pass,false);
console.log(JSON.stringify({suite:'P9-INDEPENDENT-AUDIT',pass:10,total:10,score:100}));
