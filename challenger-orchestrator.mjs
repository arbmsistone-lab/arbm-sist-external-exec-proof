import fs from 'node:fs';
import {comparePaired} from './comparative-challenger-engine.mjs';
import {appendEvidence} from './universal-radar-evidence-ledger.mjs';
const queuePath='challenger-queue.json';
const load=()=>fs.existsSync(queuePath)?JSON.parse(fs.readFileSync(queuePath,'utf8')):{schema:'arbm-challenger-queue-v1',items:[]};
export function enqueueStrategy(strategy){
  const q=load(); const now=new Date().toISOString(); const existing=new Set(q.items.map(x=>x.key)); let added=0;
  for(const d of strategy.decisions||[]){
    if(d.action!=='BENCHMARK_NOW'||d.pricingState!=='FREE'||existing.has(d.key)) continue;
    q.items.push({key:d.key,name:d.name,domain:d.domain,status:'QUEUED_MICRO_SHADOW',createdAt:now,primaryEvidence:d.primaryEvidence===true}); existing.add(d.key); added++;
  }
  q.updatedAt=now; fs.writeFileSync(queuePath,JSON.stringify(q,null,2)); return {added,total:q.items.length};
}
export function recordChallenge({key,incumbent,candidate,candidateMeta,grade='microShadow'}){
  const result=comparePaired({incumbent,candidate,candidateMeta,grade}); const q=load(); const item=q.items.find(x=>x.key===key);
  if(item){item.status=result.decision; item.lastResultHash=result.artifactHash; item.updatedAt=new Date().toISOString();}
  q.updatedAt=new Date().toISOString(); fs.writeFileSync(queuePath,JSON.stringify(q,null,2));
  const evidence=appendEvidence({type:'CHALLENGER_RESULT',key,grade,decision:result.decision,artifactHash:result.artifactHash,gates:result.gates,quality:result.quality,latency:result.latency});
  return {...result,evidenceSequence:evidence.sequence,evidenceHash:evidence.entryHash};
}
