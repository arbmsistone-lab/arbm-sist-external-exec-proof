import fs from 'node:fs';
import {appendEvidence,verifyLedger} from './universal-radar-evidence-ledger.mjs';
const path='universal-radar-evidence-ledger.jsonl';
const backup=fs.existsSync(path)?fs.readFileSync(path,'utf8'):null;
try{
  fs.writeFileSync(path,'');
  const a=appendEvidence({run:'a',pass:true}); const b=appendEvidence({run:'b',pass:true});
  const ok=verifyLedger();
  if(!ok.ok||ok.entries!==2||b.previousHash!==a.entryHash) throw new Error('LEDGER_CHAIN_FAIL');
  const lines=fs.readFileSync(path,'utf8').trim().split(/\r?\n/); const x=JSON.parse(lines[0]); x.payload.pass=false; lines[0]=JSON.stringify(x); fs.writeFileSync(path,lines.join('\n')+'\n');
  if(verifyLedger().ok) throw new Error('LEDGER_TAMPER_NOT_DETECTED');
  fs.writeFileSync(path,'{bad-json\n');
  const parsed=verifyLedger();
  if(parsed.ok||parsed.reason!=='PARSE') throw new Error('LEDGER_PARSE_FAIL_CLOSED_MISSING');
  let blocked=false;
  try{appendEvidence({run:'must-not-append'});}catch(e){blocked=String(e.message).includes('EVIDENCE_LEDGER_HEAD_PARSE_ERROR');}
  if(!blocked) throw new Error('LEDGER_CORRUPT_HEAD_APPEND_NOT_BLOCKED');
  console.log('UNIVERSAL_RADAR_EVIDENCE_LEDGER_PASS');
} finally { if(backup===null) fs.rmSync(path,{force:true}); else fs.writeFileSync(path,backup); }
