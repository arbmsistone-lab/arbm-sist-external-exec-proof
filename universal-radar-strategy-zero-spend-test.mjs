import fs from 'node:fs';
import crypto from 'node:crypto';
import {analyzeStrategy} from './universal-radar-strategy-brain.mjs';
const path='universal-radar-registry.json'; const existed=fs.existsSync(path); const backup=existed?fs.readFileSync(path,'utf8'):null;
const keyOf=x=>crypto.createHash('sha256').update([x.sourceId,x.externalId,x.name,x.domain].join('|')).digest('hex');
const mk=(id,pricing)=>({sourceId:'test',externalId:id,name:id+' release capability reasoning tool',domain:'ai-providers',primarySource:true,summary:'release capability',rawMeta:{pricing}});
try{
  const unknown=mk('unknown',undefined), free=mk('free',{prompt:0,completion:0}), paid=mk('paid',{prompt:1,completion:1});
  const events=[unknown,free,paid].map(x=>({key:keyOf(x),name:x.name,domain:x.domain,type:'NEW',severity:'LOW',action:'DISCOVER',reasons:['new_candidate']}));
  const out=analyzeStrategy({events},{items:[unknown,free,paid]}); const by=Object.fromEntries(out.decisions.map(x=>[x.name.split(' ')[0],x.action]));
  if(by.unknown!=='COST_REVIEW') throw new Error('UNKNOWN_COST_REACHED_BENCHMARK');
  if(by.free!=='BENCHMARK_NOW') throw new Error('FREE_NOT_BENCHMARKED');
  if(by.paid!=='IGNORE') throw new Error('PAID_NOT_BLOCKED');
  console.log('UNIVERSAL_RADAR_STRATEGY_ZERO_SPEND_PASS');
} finally { if(existed) fs.writeFileSync(path,backup); else fs.rmSync(path,{force:true}); }
