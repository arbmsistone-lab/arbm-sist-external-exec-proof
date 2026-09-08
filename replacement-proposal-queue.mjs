import fs from 'node:fs';
import {evaluateReplacementProposal} from './replacement-proposal-gate.mjs';
import {appendEvidence,verifyLedger} from './universal-radar-evidence-ledger.mjs';
import {withFileLock} from './file-mutation-lock.mjs';
const path='replacement-proposals.json';
const lockPath=path+'.mutation.lock';
const load=()=>fs.existsSync(path)?JSON.parse(fs.readFileSync(path,'utf8')):{schema:'arbm-replacement-proposals-v1',items:[]};
function atomicWrite(q){const tmp=path+'.tmp-'+process.pid;const fd=fs.openSync(tmp,'w');try{fs.writeFileSync(fd,JSON.stringify(q,null,2));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(tmp,path);}
export function submitReplacementProposal(input){return withFileLock(lockPath,()=>{
  const gate=evaluateReplacementProposal(input); const q=load();
  if(!gate.approved) return {queued:false,gate};
  const ledgerCheck=verifyLedger(); if(!ledgerCheck.ok) return {queued:false,gate,reasons:['EVIDENCE_LEDGER_INVALID']};
  const exists=q.items.some(x=>x.proposalHash===gate.proposalHash);
  const original=structuredClone(q); if(!exists) q.items.push({proposalHash:gate.proposalHash,challengerResultHash:gate.challengerResultHash,domain:gate.domain,status:'PENDING_P9',createdAt:new Date().toISOString(),incumbentIdentity:gate.incumbentIdentity,challengerIdentity:gate.challengerIdentity});
  q.updatedAt=new Date().toISOString(); atomicWrite(q);
  let evidence; try{evidence=appendEvidence({type:'REPLACEMENT_PROPOSAL',domain:gate.domain,proposalHash:gate.proposalHash,challengerResultHash:gate.challengerResultHash,status:'PENDING_P9'});}catch(e){atomicWrite(original);throw e;}
  return {queued:!exists,duplicate:exists,total:q.items.length,gate,evidenceHash:evidence.entryHash};
});}
