import fs from 'node:fs';
const policy=JSON.parse(fs.readFileSync('universal-radar-policy.json','utf8'));
const now=new Date().toISOString();
export function normalizeCandidate(x={}){
  return {
    id:String(x.id||x.name||'unknown').toLowerCase().replace(/[^a-z0-9._-]+/g,'-'),
    name:String(x.name||x.id||'unknown'),
    domain:String(x.domain||'unknown'),
    vendor:String(x.vendor||'unknown'),
    region:String(x.region||'global'),
    freeTier:x.freeTier===true,
    trialOnly:x.trialOnly===true,
    cardRequired:x.cardRequired===true,
    billingClear:x.billingClear!==false,
    primarySource:x.primarySource===true,
    quality:Number(x.quality||0), reliability:Number(x.reliability||0),
    latency:Number(x.latency||0), availability:Number(x.availability||0),
    security:Number(x.security||0), privacy:Number(x.privacy||0),
    lowRamSuitability:Number(x.lowRamSuitability||0),
    checkpointSupport:x.checkpointSupport===true, resumeSupport:x.resumeSupport===true,
    observedAt:String(x.observedAt||now), source:String(x.source||'')
  };
}
export function scoreCandidate(c){
  const n=normalizeCandidate(c);
  if(!n.freeTier||n.trialOnly||!n.billingClear) return {candidate:n,eligible:false,score:-999,reason:'ZERO_SPEND_FAIL'};
  const base=n.quality*0.25+n.reliability*0.2+n.availability*0.15+n.security*0.12+n.privacy*0.08+n.lowRamSuitability*0.1;
  const latencyBonus=n.latency>0?Math.max(0,10-Math.log10(n.latency+1)*2):0;
  const resilience=(n.checkpointSupport?4:0)+(n.resumeSupport?4:0)+(n.primarySource?3:0);
  const penalties=(n.cardRequired?8:0)+(n.vendor==='unknown'?2:0);
  return {candidate:n,eligible:true,score:Number((base+latencyBonus+resilience-penalties).toFixed(3)),reason:'ELIGIBLE'};
}
export function rankCandidates(items=[]){
  const seen=new Map();
  for(const raw of items){
    const s=scoreCandidate(raw); const prev=seen.get(s.candidate.id);
    if(!prev||s.score>prev.score) seen.set(s.candidate.id,s);
  }
  return [...seen.values()].sort((a,b)=>b.score-a.score);
}
export function canPromote(stage,next){
  const p=policy.candidatePipeline; const a=p.indexOf(stage), b=p.indexOf(next);
  if(a<0||b<0||b!==a+1) return false;
  if(stage==='CANDIDATE'&&next==='STABLE_OR_REJECT') return false;
  return true;
}
