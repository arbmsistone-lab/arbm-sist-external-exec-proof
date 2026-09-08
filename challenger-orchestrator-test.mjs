import fs from 'node:fs';
import {enqueueStrategy,recordChallenge} from './challenger-orchestrator.mjs';
const q='challenger-queue.json'; const l='universal-radar-evidence-ledger.jsonl';
const qb=fs.existsSync(q)?fs.readFileSync(q,'utf8'):null; const lb=fs.existsSync(l)?fs.readFileSync(l,'utf8'):null;
const mk=(n,lat)=>Array.from({length:n},(_,i)=>({id:'t'+i,pass:true,integrity:true,latencyMs:lat+i}));
try{
  fs.writeFileSync(q,JSON.stringify({schema:'arbm-challenger-queue-v1',items:[]},null,2));
  const e=enqueueStrategy({decisions:[{key:'k1',name:'Free X',domain:'coding-models',action:'BENCHMARK_NOW',pricingState:'FREE',primaryEvidence:true},{key:'k2',name:'Unknown Y',domain:'coding-models',action:'BENCHMARK_NOW',pricingState:'UNKNOWN',primaryEvidence:true}]});
  if(e.added!==1||e.total!==1) throw new Error('QUEUE_ZERO_SPEND_FAIL');
  const r=recordChallenge({key:'k1',incumbent:mk(4,120),candidate:mk(4,90),candidateMeta:{zeroSpendVerified:true,primaryEvidence:true},grade:'microShadow'});
  if(r.decision!=='ADVANCE_TO_REPLACEMENT_GRADE'||!r.evidenceHash) throw new Error('CHALLENGE_RECORD_FAIL');
  const after=JSON.parse(fs.readFileSync(q,'utf8')); if(after.items[0].status!=='ADVANCE_TO_REPLACEMENT_GRADE') throw new Error('QUEUE_STATUS_FAIL');
  console.log('CHALLENGER_ORCHESTRATOR_PASS');
} finally { if(qb===null) fs.rmSync(q,{force:true}); else fs.writeFileSync(q,qb); if(lb===null) fs.rmSync(l,{force:true}); else fs.writeFileSync(l,lb); }
