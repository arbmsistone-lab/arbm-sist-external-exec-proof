import fs from 'node:fs';
import {evaluateReplacementProposal} from './replacement-proposal-gate.mjs';
import {appendEvidence} from './universal-radar-evidence-ledger.mjs';
const path='replacement-proposals.json';
const load=()=>fs.existsSync(path)?JSON.parse(fs.readFileSync(path,'utf8')):{schema:'arbm-replacement-proposals-v1',items:[]};
export function submitReplacementProposal(input){
  const gate=evaluateReplacementProposal(input); const q=load();
  if(!gate.approved) return {queued:false,gate};
  const exists=q.items.some(x=>x.proposalHash===gate.proposalHash);
  if(!exists) q.items.push({proposalHash:gate.proposalHash,domain:gate.domain,status:'PENDING_P9',createdAt:new Date().toISOString(),incumbentIdentity:gate.incumbentIdentity,challengerIdentity:gate.challengerIdentity});
  q.updatedAt=new Date().toISOString(); fs.writeFileSync(path,JSON.stringify(q,null,2));
  const evidence=appendEvidence({type:'REPLACEMENT_PROPOSAL',domain:gate.domain,proposalHash:gate.proposalHash,status:'PENDING_P9'});
  return {queued:!exists,duplicate:exists,total:q.items.length,gate,evidenceHash:evidence.entryHash};
}
