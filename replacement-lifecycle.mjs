import fs from 'node:fs';
import {verifyLedger} from './universal-radar-evidence-ledger.mjs';
const queuePath='replacement-proposals.json';
const ledgerPath='universal-radar-evidence-ledger.jsonl';
const loadQueue=()=>fs.existsSync(queuePath)?JSON.parse(fs.readFileSync(queuePath,'utf8')):{schema:'arbm-replacement-proposals-v1',items:[]};
const readEntries=()=>fs.existsSync(ledgerPath)?fs.readFileSync(ledgerPath,'utf8').split(/\r?\n/).filter(Boolean).map(x=>JSON.parse(x)):[];
function atomicWrite(q){const tmp=queuePath+'.tmp-'+process.pid;const fd=fs.openSync(tmp,'w');try{fs.writeFileSync(fd,JSON.stringify(q,null,2));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(tmp,queuePath);}
export function deriveLifecycle(proposalHash){
  const ledger=verifyLedger(); if(!ledger.ok) return {ok:false,status:'BLOCKED_LEDGER_INVALID'};
  const entries=readEntries().filter(e=>e.payload?.proposalHash===proposalHash);
  let status='UNKNOWN';
  if(entries.some(e=>e.payload?.type==='REPLACEMENT_PROPOSAL')) status='PENDING_P9';
  if(entries.some(e=>e.payload?.type==='REPLACEMENT_CERTIFIED')) status='CERTIFIED';
  if(entries.some(e=>e.payload?.type==='INCUMBENT_PROMOTED')) status='PROMOTED';
  if(entries.some(e=>e.payload?.type==='INCUMBENT_ROLLED_BACK')) status='ROLLED_BACK';
  return {ok:true,status,entries:entries.map(e=>e.entryHash)};
}
export function reconcileQueue(){
  const ledger=verifyLedger(); if(!ledger.ok) return {ok:false,reason:'EVIDENCE_LEDGER_INVALID'};
  const q=loadQueue(); let changed=0;
  for(const item of q.items||[]){
    const life=deriveLifecycle(item.proposalHash); if(!life.ok) return {ok:false,reason:'EVIDENCE_LEDGER_INVALID'};
    const target=life.status==='UNKNOWN'?'ORPHANED_NO_LEDGER':life.status;
    if(item.status!==target){item.status=target;item.lifecycleEvidence=life.entries;changed++;}
  }
  if(changed){q.updatedAt=new Date().toISOString();atomicWrite(q);}
  return {ok:true,changed,total:(q.items||[]).length};
}
