import {isDue,resourceDecision,schedulerTick} from './universal-radar-scheduler.mjs';
const state={lastRuns:{standard:new Date().toISOString()}};
if(isDue('standard',Date.now(),state)) throw new Error('CADENCE_FAIL');
if(!isDue('standard',Date.now()+7*60*60*1000,state)) throw new Error('CADENCE_WINDOW_FAIL');
const r=resourceDecision('standard');
if(typeof r.run!=='boolean'||!Number.isFinite(r.freeMiB)) throw new Error('RESOURCE_GUARD_FAIL');
const out=await schedulerTick('standard',true);
if(r.run){ if(!out.ran||!out.result?.pass||!out.result?.ledgerOk) throw new Error('SCHEDULER_TICK_FAIL'); }
else { if(out.ran||!['LOW_RAM','DEEP_SCAN_LOW_RAM'].includes(out.reason)) throw new Error('LOW_RAM_GUARD_FAIL'); }
const skipped=await schedulerTick('standard',false);
if(skipped.ran||!['NOT_DUE','LOW_RAM','DEEP_SCAN_LOW_RAM'].includes(skipped.reason)) throw new Error('SCHEDULER_IDEMPOTENCE_FAIL');
console.log('UNIVERSAL_RADAR_SCHEDULER_PASS');
