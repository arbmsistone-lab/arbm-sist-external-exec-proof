import fs from 'node:fs';
import crypto from 'node:crypto';
const policy=JSON.parse(fs.readFileSync('universal-radar-strategy-policy.json','utf8'));
const registryPath='universal-radar-registry.json';
const hash=v=>crypto.createHash('sha256').update(String(v)).digest('hex');
const keyOf=x=>hash([x.sourceId,x.externalId,x.name,x.domain].join('|'));
const loadRegistry=()=>fs.existsSync(registryPath)?JSON.parse(fs.readFileSync(registryPath,'utf8')):{items:{}};
const sev={INFO:0,LOW:10,MEDIUM:28,HIGH:58,CRITICAL:88};
const stageRank={DISCOVER:0,COLLECT:1,VERIFY:2,NORMALIZE:3,DEDUPLICATE:4,CANDIDATE:5,SECURITY_CHECK:6,COST_CHECK:7,PRIVACY_CHECK:8,LICENSE_CHECK:9,COMPATIBILITY_CHECK:10,BENCHMARK:11,SHADOW:12,CANARY:13,STABLE_OR_REJECT:14,MONITOR:15,LEARN:16};
function pricingState(item){
  const p=item?.rawMeta?.pricing;
  if(!p||typeof p!=='object') return 'UNKNOWN';
  const vals=Object.values(p).map(v=>Number(v)).filter(Number.isFinite);
  if(!vals.length) return 'UNKNOWN';
  return vals.every(v=>v===0)?'FREE':'PAID_OR_MIXED';
}
function domainWeight(domain){return Number(policy.domainWeights?.[domain]??(policy.coreDomains?.includes(domain)?7:2));}
function opportunityScore(event,item,previous){
  let s=domainWeight(event.domain)*5;
  if(event.type==='NEW') s+=8;
  if(event.action==='BENCHMARK_RECHECK') s+=18;
  if(item?.primarySource) s+=10;
  if(pricingState(item)==='FREE') s+=15;
  if(/release|version|capabilit|reasoning|tool|multimodal/i.test(`${item?.name||''} ${item?.summary||''}`)) s+=10;
  if((stageRank[previous?.stage]??0)>=(stageRank.BENCHMARK)) s+=8;
  return Math.max(0,Math.min(100,s));
}
function threatScore(event){
  let s=sev[event.severity]??10;
  if(event.action==='QUARANTINE') s+=20;
  if(event.action==='SECURITY_RECHECK') s+=15;
  if(event.action==='COST_RECHECK') s+=12;
  if(event.before==='FREE'&&event.after!=='FREE') s+=18;
  return Math.min(100,s);
}
function chooseAction(event,item,previous,opp,threat){
  const t=policy.thresholds; const price=pricingState(item);
  if(event.action==='QUARANTINE'||threat>=90) return 'QUARANTINE';
  if(event.action==='SECURITY_RECHECK'||threat>=t.threatHighAt) return 'SECURITY_REVIEW';
  if(event.action==='COST_RECHECK') return 'COST_REVIEW';
  if(policy.rules?.requireKnownZeroCost&&opp>=t.benchmarkNowAt&&price!=='FREE'){
    return price==='UNKNOWN'?'COST_REVIEW':'IGNORE';
  }
  const replaceReady=opp>=t.replaceCandidateAt&&price==='FREE'&&item?.primarySource===true&&(stageRank[previous?.stage]??0)>=stageRank.BENCHMARK;
  if(replaceReady) return 'REPLACE_CANDIDATE';
  if(opp>=t.benchmarkNowAt) return 'BENCHMARK_NOW';
  if(opp<t.ignoreBelow) return 'IGNORE';
  if(opp<t.watchBelow) return 'WATCH';
  return 'VERIFY';
}
export function analyzeStrategy(changeReport,collection){
  const reg=loadRegistry(); const byKey=new Map((collection.items||[]).map(x=>[keyOf(x),x]));
  const decisions=(changeReport.events||[]).map(event=>{
    const item=byKey.get(event.key)||{}; const previous=reg.items?.[event.key]||null;
    const opportunity=opportunityScore(event,item,previous); const threat=threatScore(event);
    const action=chooseAction(event,item,previous,opportunity,threat);
    return {key:event.key,name:event.name,domain:event.domain,eventType:event.type,severity:event.severity,opportunity,threat,action,pricingState:pricingState(item),primaryEvidence:item?.primarySource===true,previousStage:previous?.stage||null,reasons:event.reasons||[]};
  }).sort((a,b)=>Math.max(b.opportunity,b.threat)-Math.max(a.opportunity,a.threat));
  return {
    schema:'arbm-universal-radar-strategy-brain-v1',total:decisions.length,
    benchmarkNow:decisions.filter(x=>x.action==='BENCHMARK_NOW').length,
    replaceCandidates:decisions.filter(x=>x.action==='REPLACE_CANDIDATE').length,
    securityReviews:decisions.filter(x=>x.action==='SECURITY_REVIEW').length,
    costReviews:decisions.filter(x=>x.action==='COST_REVIEW').length,
    quarantines:decisions.filter(x=>x.action==='QUARANTINE').length,
    decisions
  };
}
