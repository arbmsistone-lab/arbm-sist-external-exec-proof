import {rankCandidates,canPromote} from './universal-radar-engine.mjs';
const ranked=rankCandidates([
  {name:'A',domain:'ai-providers',vendor:'v1',freeTier:true,billingClear:true,quality:9,reliability:9,availability:9,security:9,privacy:8,lowRamSuitability:10,checkpointSupport:true,resumeSupport:true,primarySource:true,latency:200},
  {name:'B',domain:'ai-providers',vendor:'v2',freeTier:false,billingClear:true,quality:10,reliability:10,availability:10,security:10,privacy:10,lowRamSuitability:10,checkpointSupport:true,resumeSupport:true,primarySource:true,latency:100},
  {name:'C',domain:'remote-runners',vendor:'v3',freeTier:true,trialOnly:true,billingClear:true,quality:10,reliability:10,availability:10,security:9,privacy:9,lowRamSuitability:10,checkpointSupport:true,resumeSupport:true,primarySource:true,latency:150}
]);
if(ranked[0].candidate.name!=='A'||!ranked[0].eligible) throw new Error('RANKING_FAIL');
if(ranked.find(x=>x.candidate.name==='B')?.eligible!==false) throw new Error('PAID_ROUTE_ACCEPTED');
if(ranked.find(x=>x.candidate.name==='C')?.eligible!==false) throw new Error('TRIAL_ROUTE_ACCEPTED');
if(!canPromote('DISCOVER','COLLECT')) throw new Error('PIPELINE_FORWARD_FAIL');
if(canPromote('DISCOVER','BENCHMARK')) throw new Error('PIPELINE_SKIP_ALLOWED');
console.log('UNIVERSAL_RADAR_ENGINE_PASS');
