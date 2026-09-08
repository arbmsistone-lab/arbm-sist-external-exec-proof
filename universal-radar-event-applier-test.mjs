import fs from 'node:fs';
import {applyEvents} from './universal-radar-event-applier.mjs';
const path='universal-radar-registry.json';
const existed=fs.existsSync(path); const backup=existed?fs.readFileSync(path,'utf8'):null; const key='fixture-key';
try{
  const fixture={schema:'arbm-universal-radar-registry-v1',items:{[key]:{stage:'STABLE_OR_REJECT',quarantined:false}},events:[]};
  fs.writeFileSync(path,JSON.stringify(fixture,null,2));
  const r=applyEvents({events:[{key,severity:'CRITICAL',action:'QUARANTINE',reasons:['shutdown']}]});
  const after=JSON.parse(fs.readFileSync(path,'utf8'));
  if(r.quarantined!==1||after.items[key].stage!=='VERIFY'||after.items[key].quarantined!==true) throw new Error('QUARANTINE_APPLY_FAIL');
  const beforeBad=fs.readFileSync(path,'utf8');
  let blocked=false; try{applyEvents({events:[{key,action:'UNKNOWN'}]});}catch(e){blocked=String(e.message).includes('RADAR_EVENT_INVALID');}
  if(!blocked||fs.readFileSync(path,'utf8')!==beforeBad) throw new Error('MALFORMED_EVENT_NOT_FAIL_CLOSED');
  console.log('UNIVERSAL_RADAR_EVENT_APPLIER_PASS');
} finally {
  if(existed) fs.writeFileSync(path,backup); else fs.rmSync(path,{force:true});
}
