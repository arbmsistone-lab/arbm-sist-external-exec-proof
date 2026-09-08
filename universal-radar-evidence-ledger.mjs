import fs from 'node:fs';
import crypto from 'node:crypto';
const ledgerPath='universal-radar-evidence-ledger.jsonl';
const lockPath=ledgerPath+'.lock';
const sleepMs=ms=>Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,ms);
function withLock(fn){let held=false;for(let i=0;i<100&&!held;i++){try{fs.mkdirSync(lockPath);held=true;}catch(e){if(e?.code!=='EEXIST') throw e;sleepMs(10);}}if(!held) throw new Error('EVIDENCE_LEDGER_LOCK_TIMEOUT');try{return fn();}finally{fs.rmSync(lockPath,{recursive:true,force:true});}}
const hash=(v)=>crypto.createHash('sha256').update(String(v)).digest('hex');
export const validLedgerHash=x=>/^(?:sha256:)?[0-9a-f]{64}$/i.test(String(x||''));
const readLines=()=>fs.existsSync(ledgerPath)?fs.readFileSync(ledgerPath,'utf8').split(/\r?\n/).filter(Boolean):[];
export function appendEvidence(payload){return withLock(()=>{
  const lines=readLines(); let prev=null; try{prev=lines.length?JSON.parse(lines.at(-1)):null;}catch{throw new Error('EVIDENCE_LEDGER_HEAD_PARSE_ERROR');}
  const base={schema:'arbm-radar-evidence-v1',sequence:lines.length+1,createdAt:new Date().toISOString(),previousHash:prev?.entryHash||null,payload};
  const entryHash=hash(JSON.stringify(base)); const entry={...base,entryHash};
  const fd=fs.openSync(ledgerPath,'a'); try{fs.writeFileSync(fd,JSON.stringify(entry)+'\n');fs.fsyncSync(fd);} finally{fs.closeSync(fd);}
  return entry;
});}
export function verifyLedger(){
  const lines=readLines(); let previousHash=null;
  for(let i=0;i<lines.length;i++){
    let entry; try{entry=JSON.parse(lines[i]);}catch{return {ok:false,index:i,reason:'PARSE'};} const {entryHash,...base}=entry;
    if(entry.sequence!==i+1) return {ok:false,index:i,reason:'SEQUENCE'};
    if(entry.previousHash!==previousHash) return {ok:false,index:i,reason:'CHAIN'};
    if(hash(JSON.stringify(base))!==entryHash) return {ok:false,index:i,reason:'HASH'};
    previousHash=entryHash;
  }
  return {ok:true,entries:lines.length,headHash:previousHash};
}

export function findEvidence(entryHash){
  const check=verifyLedger(); if(!check.ok) return {ok:false,reason:'LEDGER_INVALID'};
  for(const line of readLines()){const e=JSON.parse(line);if(e.entryHash===entryHash) return {ok:true,entry:e};}
  return {ok:false,reason:'EVIDENCE_NOT_FOUND'};
}
