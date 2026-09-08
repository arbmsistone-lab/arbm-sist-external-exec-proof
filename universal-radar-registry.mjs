import fs from 'node:fs';
import crypto from 'node:crypto';
const registryPath='universal-radar-registry.json';
const hash=(v)=>crypto.createHash('sha256').update(String(v)).digest('hex');
const load=()=>fs.existsSync(registryPath)?JSON.parse(fs.readFileSync(registryPath,'utf8')):{schema:'arbm-universal-radar-registry-v1',items:{},updatedAt:null};
const keyOf=(x)=>hash([x.sourceId,x.externalId,x.name,x.domain].join('|'));
export function mergeCollection(collection){
  const reg=load(); const now=new Date().toISOString();
  let discovered=0,changed=0,seen=0;
  for(const item of collection.items||[]){
    const key=keyOf(item); const contentHash=hash(JSON.stringify(item)); const prev=reg.items[key];
    if(!prev){ discovered++; reg.items[key]={...item,key,contentHash,stage:'DISCOVER',firstSeenAt:now,lastSeenAt:now,seenCount:1,changeCount:0}; }
    else { seen++; const didChange=prev.contentHash!==contentHash; if(didChange) changed++; reg.items[key]={...prev,...item,contentHash,lastSeenAt:now,seenCount:(prev.seenCount||0)+1,changeCount:(prev.changeCount||0)+(didChange?1:0)}; }
  }
  reg.updatedAt=now; fs.writeFileSync(registryPath,JSON.stringify(reg,null,2));
  return {schema:reg.schema,total:Object.keys(reg.items).length,discovered,changed,seen,updatedAt:now};
}
