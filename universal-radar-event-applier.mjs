import fs from 'node:fs';
import {recheckStageFor} from './universal-radar-change-intelligence.mjs';
const registryPath='universal-radar-registry.json';
const load=()=>fs.existsSync(registryPath)?JSON.parse(fs.readFileSync(registryPath,'utf8')):{schema:'arbm-universal-radar-registry-v1',items:{}};
function atomicWrite(reg){const tmp=registryPath+'.tmp-'+process.pid;const fd=fs.openSync(tmp,'w');try{fs.writeFileSync(fd,JSON.stringify(reg,null,2));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(tmp,registryPath);}
const allowedActions=new Set(['QUARANTINE','SECURITY_RECHECK','COST_RECHECK','BENCHMARK_RECHECK','VERIFY','DISCOVER','NONE']);
export function applyEvents(report){
  const reg=load(); const now=new Date().toISOString(); let applied=0, quarantined=0, reopened=0;
  reg.events=Array.isArray(reg.events)?reg.events:[];
  if(!report||!Array.isArray(report.events)) throw new Error('RADAR_EVENTS_INVALID');
  for(const event of report.events){
    if(!event||typeof event.key!=='string'||!allowedActions.has(event.action)) throw new Error('RADAR_EVENT_INVALID');
    const item=reg.items?.[event.key]; if(!item) continue;
    const target=recheckStageFor(event.action);
    if(event.action==='QUARANTINE'){
      item.quarantined=true; item.quarantineReason=event.reasons; item.stage=target; quarantined++;
    } else if(event.action!=='NONE'){
      item.stage=target; reopened++;
    }
    item.lastChangeSeverity=event.severity; item.lastChangeAction=event.action; item.lastChangeAt=now;
    reg.events.push({...event,appliedAt:now}); applied++;
  }
  reg.events=reg.events.slice(-5000); reg.updatedAt=now;
  atomicWrite(reg);
  return {schema:'arbm-universal-radar-event-apply-v1',applied,quarantined,reopened,updatedAt:now};
}
