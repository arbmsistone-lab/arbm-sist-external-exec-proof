import fs from 'node:fs';
const regPath='incumbent-registry.json', qPath='replacement-proposals.json';
const regBackup=fs.readFileSync(regPath,'utf8'); const qBackup=fs.existsSync(qPath)?fs.readFileSync(qPath,'utf8'):null; const ledgerPath='universal-radar-evidence-ledger.jsonl'; const ledgerBackup=fs.existsSync(ledgerPath)?fs.readFileSync(ledgerPath,'utf8'):null;
try{
  const reg=JSON.parse(regBackup); reg.domains['coding-models']={status:'VERIFIED',active:{id:'incumbent-a',version:'7',artifactSha256:'sha256:'+'a'.repeat(64),activatedAt:'2026-09-01T00:00:00Z',zeroSpendVerified:true}}; fs.writeFileSync(regPath,JSON.stringify(reg,null,2));
  fs.rmSync(qPath,{force:true});
  const mod=await import(`./replacement-proposal-queue.mjs?x=${Date.now()}`);
  const result={grade:'replacementGrade',decision:'REPLACEMENT_CANDIDATE',replacementApplied:false,gates:{sampleOk:true,pairedOk:true,integrityOk:true}};
  const challenger={id:'candidate-x',version:'1',artifactSha256:'sha256:'+'b'.repeat(64),activatedAt:'2026-09-08T00:00:00Z',zeroSpendVerified:true};
  const a=mod.submitReplacementProposal({domain:'coding-models',challengerResult:result,challengerIdentity:challenger});
  const b=mod.submitReplacementProposal({domain:'coding-models',challengerResult:result,challengerIdentity:challenger});
  if(!a.queued||!b.duplicate||a.gate.action!=='OPEN_P9_REPLACEMENT_PROPOSAL'||!a.gate.challengerResultHash) throw new Error('PROPOSAL_QUEUE_FAIL');
  const stable=fs.readFileSync(qPath,'utf8'); fs.writeFileSync('universal-radar-evidence-ledger.jsonl','{corrupt\n');
  const blocked=mod.submitReplacementProposal({domain:'coding-models',challengerResult:result,challengerIdentity:{...challenger,id:'candidate-y'}});
  if(blocked.queued||!blocked.reasons?.includes('EVIDENCE_LEDGER_INVALID')||fs.readFileSync(qPath,'utf8')!==stable) throw new Error('QUEUE_LEDGER_FAIL_CLOSED');
  console.log('REPLACEMENT_PROPOSAL_QUEUE_PASS');
} finally {fs.writeFileSync(regPath,regBackup); if(qBackup===null) fs.rmSync(qPath,{force:true}); else fs.writeFileSync(qPath,qBackup); fs.rmSync(qPath+'.mutation.lock',{recursive:true,force:true}); if(ledgerBackup===null) fs.rmSync(ledgerPath,{force:true}); else fs.writeFileSync(ledgerPath,ledgerBackup);}
