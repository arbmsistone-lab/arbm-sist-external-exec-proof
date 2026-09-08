import fs from 'node:fs';
import os from 'node:os';
import {runRadarCycle} from './universal-radar-cycle.mjs';
const policy=JSON.parse(fs.readFileSync('universal-radar-scheduler-policy.json','utf8'));
const statePath='universal-radar-scheduler-state.json';
const load=()=>fs.existsSync(statePath)?JSON.parse(fs.readFileSync(statePath,'utf8')):{schema:'arbm-radar-scheduler-state-v1',lastRuns:{},failures:0};
function save(state){const tmp=statePath+'.tmp-'+process.pid;const fd=fs.openSync(tmp,'w');try{fs.writeFileSync(fd,JSON.stringify(state,null,2));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(tmp,statePath);}
const freeMiB=()=>Math.round(os.freemem()/1024/1024);
export function isDue(tier='standard',now=Date.now(),state=load()){
  const minutes=Number(policy.cadenceMinutes?.[tier]||360); const last=Date.parse(state.lastRuns?.[tier]||0);
  return !Number.isFinite(last)||now-last>=minutes*60000;
}
export function resourceDecision(tier='standard'){
  const free=freeMiB(); const min=Number(policy.resourceGuards.minimumFreeRamMiB||768);
  if(free<min) return {run:false,reason:'LOW_RAM',freeMiB:free};
  if(tier==='deep'&&policy.resourceGuards.skipDeepScanOnLowRam&&free<min*2) return {run:false,reason:'DEEP_SCAN_LOW_RAM',freeMiB:free};
  return {run:true,reason:'OK',freeMiB:free};
}
export async function schedulerTick(tier='standard',force=false){
  const state=load(); if(!force&&!isDue(tier,Date.now(),state)) return {ran:false,reason:'NOT_DUE'};
  const resources=resourceDecision(tier); if(!resources.run) return {ran:false,...resources};
  try{ const result=await runRadarCycle(); state.lastRuns[tier]=new Date().toISOString(); state.failures=0; state.lastResult={pass:result.pass,evidenceHash:result.evidenceHash}; save(state); return {ran:true,...resources,result}; }
  catch(e){ state.failures=(state.failures||0)+1; state.lastError=String(e?.message||e).slice(0,400); save(state); throw e; }
}
