import fs from 'node:fs';
import crypto from 'node:crypto';
const ledgerPath='universal-radar-evidence-ledger.jsonl';
const hash=(v)=>crypto.createHash('sha256').update(String(v)).digest('hex');
const readLines=()=>fs.existsSync(ledgerPath)?fs.readFileSync(ledgerPath,'utf8').split(/\r?\n/).filter(Boolean):[];
export function appendEvidence(payload){
  const lines=readLines(); const prev=lines.length?JSON.parse(lines.at(-1)):null;
  const base={schema:'arbm-radar-evidence-v1',sequence:lines.length+1,createdAt:new Date().toISOString(),previousHash:prev?.entryHash||null,payload};
  const entryHash=hash(JSON.stringify(base)); const entry={...base,entryHash};
  fs.appendFileSync(ledgerPath,JSON.stringify(entry)+'\n');
  return entry;
}
export function verifyLedger(){
  const lines=readLines(); let previousHash=null;
  for(let i=0;i<lines.length;i++){
    const entry=JSON.parse(lines[i]); const {entryHash,...base}=entry;
    if(entry.sequence!==i+1) return {ok:false,index:i,reason:'SEQUENCE'};
    if(entry.previousHash!==previousHash) return {ok:false,index:i,reason:'CHAIN'};
    if(hash(JSON.stringify(base))!==entryHash) return {ok:false,index:i,reason:'HASH'};
    previousHash=entryHash;
  }
  return {ok:true,entries:lines.length,headHash:previousHash};
}
