import fs from 'node:fs';
import crypto from 'node:crypto';
const registryPath='universal-radar-registry.json';
const hash=(v)=>crypto.createHash('sha256').update(String(v)).digest('hex');
const load=()=>fs.existsSync(registryPath)?JSON.parse(fs.readFileSync(registryPath,'utf8')):{items:{}};
const keyOf=(x)=>hash([x.sourceId,x.externalId,x.name,x.domain].join('|'));
const text=(x)=>JSON.stringify(x??{}).toLowerCase();
const number=(v)=>{const n=Number(v); return Number.isFinite(n)?n:null};
export function zeroSpendState(item){
  const p=item?.rawMeta?.pricing;
  if(!p||typeof p!=='object') return 'UNKNOWN';
  const vals=Object.values(p).map(number).filter(v=>v!==null);
  if(!vals.length) return 'UNKNOWN';
  return vals.every(v=>v===0)?'FREE':'PAID_OR_MIXED';
}
function severityRank(x){return ({INFO:0,LOW:1,MEDIUM:2,HIGH:3,CRITICAL:4})[x]??0;}
function maxSeverity(a,b){return severityRank(a)>=severityRank(b)?a:b;}
export function classifyChange(prev,item){
  const before=zeroSpendState(prev), after=zeroSpendState(item);
  let severity='LOW', action='MONITOR_ONLY', reasons=[];
  const blob=text({name:item?.name,summary:item?.summary,url:item?.url,updatedAt:item?.updatedAt});
  if(!prev) return {type:'NEW',severity:'LOW',action:'DISCOVER',reasons:['new_candidate'],before,after};
  if(prev.contentHash===hash(JSON.stringify(item))) return {type:'UNCHANGED',severity:'INFO',action:'NONE',reasons:[],before,after};
  if(before!==after){reasons.push(`zero_spend:${before}->${after}`); severity='HIGH'; action='COST_RECHECK';}
  if(/deprecat|sunset|shutdown|end of life|end-of-life|discontinu|retir/.test(blob)){
    reasons.push('deprecation_or_shutdown_signal'); severity=maxSeverity(severity,'CRITICAL'); action='QUARANTINE';
  }
  if(/cve-|vulnerab|security advisory|known exploited/.test(blob)){
    reasons.push('security_signal'); severity=maxSeverity(severity,'HIGH'); if(action!=='QUARANTINE') action='SECURITY_RECHECK';
  }
  if(/price|pricing|quota|rate limit|free tier|billing/.test(blob)&&action==='MONITOR_ONLY'){
    reasons.push('commercial_or_quota_signal'); severity=maxSeverity(severity,'MEDIUM'); action='COST_RECHECK';
  }
  if(/release|version|capabilit|context window|tool use|function call|multimodal|reasoning/.test(blob)&&action==='MONITOR_ONLY'){
    reasons.push('capability_or_release_signal'); severity=maxSeverity(severity,'MEDIUM'); action='BENCHMARK_RECHECK';
  }
  if(!reasons.length){reasons.push('content_changed'); action='VERIFY';}
  return {type:'CHANGED',severity,action,reasons,before,after};
}
export function analyzeCollection(collection){
  const reg=load(); const events=[];
  for(const item of collection.items||[]){
    const key=keyOf(item); const prev=reg.items?.[key];
    const change=classifyChange(prev,item);
    if(change.type!=='UNCHANGED') events.push({key,sourceId:item.sourceId,domain:item.domain,name:item.name,...change});
  }
  return {
    schema:'arbm-universal-radar-change-intelligence-v1',
    observedAt:collection.observedAt||new Date().toISOString(),
    totalEvents:events.length,
    critical:events.filter(e=>e.severity==='CRITICAL').length,
    high:events.filter(e=>e.severity==='HIGH').length,
    medium:events.filter(e=>e.severity==='MEDIUM').length,
    events
  };
}
export function recheckStageFor(action){
  return ({QUARANTINE:'VERIFY',SECURITY_RECHECK:'SECURITY_CHECK',COST_RECHECK:'COST_CHECK',BENCHMARK_RECHECK:'BENCHMARK',VERIFY:'VERIFY',DISCOVER:'DISCOVER'})[action]||'MONITOR';
}
