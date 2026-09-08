import fs from 'node:fs';
import {applyEvents} from './universal-radar-event-applier.mjs';
const path='universal-radar-registry.json';
const backup=fs.readFileSync(path,'utf8'); const reg=JSON.parse(backup); const key=Object.keys(reg.items)[0];
try{
  reg.items[key].stage='STABLE_OR_REJECT'; reg.items[key].quarantined=false; fs.writeFileSync(path,JSON.stringify(reg,null,2));
  const r=applyEvents({events:[{key,severity:'CRITICAL',action:'QUARANTINE',reasons:['shutdown']} ]});
  const after=JSON.parse(fs.readFileSync(path,'utf8'));
  if(r.quarantined!==1||after.items[key].stage!=='VERIFY'||after.items[key].quarantined!==true) throw new Error('QUARANTINE_APPLY_FAIL');
  console.log('UNIVERSAL_RADAR_EVENT_APPLIER_PASS');
} finally { fs.writeFileSync(path,backup); }
