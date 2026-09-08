import fs from 'node:fs';
import crypto from 'node:crypto';
import {analyzeStrategy} from './universal-radar-strategy-brain.mjs';
const path='universal-radar-registry.json'; const existed=fs.existsSync(path); const backup=existed?fs.readFileSync(path,'utf8'):null;
const keyOf=x=>crypto.createHash('sha256').update([x.sourceId,x.externalId,x.name,x.domain].join('|')).digest('hex');
const free={sourceId:'test',externalId:'free-coder',name:'Free Coder release tool reasoning',domain:'coding-models',primarySource:true,summary:'new release capability',rawMeta:{pricing:{prompt:0,completion:0}}};
const paid={sourceId:'test',externalId:'paid',name:'Paid Model release',domain:'coding-models',primarySource:true,summary:'release capability',rawMeta:{pricing:{prompt:1,completion:2}}};
const risk={sourceId:'test',externalId:'risk',name:'Provider shutdown',domain:'ai-providers',primarySource:true,summary:'service shutdown',rawMeta:{pricing:{prompt:0,completion:0}}};
try{
  if(!existed) fs.writeFileSync(path,JSON.stringify({schema:'arbm-universal-radar-registry-v1',items:{},events:[]},null,2));
  const reg=JSON.parse(fs.readFileSync(path,'utf8')); reg.items[keyOf(free)]={...free,stage:'BENCHMARK'}; fs.writeFileSync(path,JSON.stringify(reg,null,2));
  const events=[
    {key:keyOf(free),name:free.name,domain:free.domain,type:'CHANGED',severity:'MEDIUM',action:'BENCHMARK_RECHECK',reasons:['capability_or_release_signal']},
    {key:keyOf(paid),name:paid.name,domain:paid.domain,type:'NEW',severity:'LOW',action:'DISCOVER',reasons:['new_candidate']},
    {key:keyOf(risk),name:risk.name,domain:risk.domain,type:'CHANGED',severity:'CRITICAL',action:'QUARANTINE',reasons:['shutdown']}
  ];
  const report=analyzeStrategy({events},{items:[free,paid,risk]});
  const a=report.decisions.find(x=>x.name===free.name);
  const b=report.decisions.find(x=>x.name===paid.name);
  const c=report.decisions.find(x=>x.name===risk.name);
  if(a?.action!=='REPLACE_CANDIDATE') throw new Error('FREE_REPLACEMENT_CANDIDATE_MISSED');
  if(b?.action==='REPLACE_CANDIDATE') throw new Error('PAID_REPLACEMENT_ALLOWED');
  if(c?.action!=='QUARANTINE') throw new Error('CRITICAL_RISK_NOT_QUARANTINED');
  console.log('UNIVERSAL_RADAR_STRATEGY_BRAIN_PASS');
} finally { if(existed) fs.writeFileSync(path,backup); else fs.rmSync(path,{force:true}); }
