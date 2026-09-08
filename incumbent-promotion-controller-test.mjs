import fs from 'node:fs';
import assert from 'node:assert/strict';
import {promoteReplacement,rollbackReplacement} from './incumbent-promotion-controller.mjs';
const registryPath='incumbent-registry.json', ledgerPath='universal-radar-evidence-ledger.jsonl';
const registryBackup=fs.readFileSync(registryPath,'utf8'); const ledgerBackup=fs.existsSync(ledgerPath)?fs.readFileSync(ledgerPath,'utf8'):null;
const d=c=>'sha256:'+c.repeat(64);
try{
  const before=JSON.parse(registryBackup).domains['ai-providers'].active;
  const challenger={id:'candidate-x',version:'2',artifactSha256:d('b'),activatedAt:'2026-09-08T16:00:00Z',zeroSpendVerified:true};
  const proposal={approved:true,action:'OPEN_P9_REPLACEMENT_PROPOSAL',proposalHash:d('c'),incumbentIdentity:before,challengerIdentity:challenger};
  const certification={status:'PASS',rollbackReady:true,evidenceHash:d('d')};
  const p=promoteReplacement({domain:'ai-providers',proposal,challengerIdentity:challenger,certification});
  assert.equal(p.promoted,true); assert.equal(JSON.parse(fs.readFileSync(registryPath,'utf8')).domains['ai-providers'].active.id,'candidate-x');
  const stale=promoteReplacement({domain:'ai-providers',proposal,challengerIdentity:challenger,certification});
  assert.equal(stale.promoted,false); assert.equal(stale.reasons.includes('INCUMBENT_CHANGED_SINCE_PROPOSAL'),true);
  const badRollback=rollbackReplacement({domain:'ai-providers',promotionHash:p.promotionHash,reason:'',evidenceHash:d('e')});
  assert.equal(badRollback.rolledBack,false); assert.equal(badRollback.reasons.includes('ROLLBACK_REASON_REQUIRED'),true);
  const rb=rollbackReplacement({domain:'ai-providers',promotionHash:p.promotionHash,reason:'canary regression',evidenceHash:d('e')});
  assert.equal(rb.rolledBack,true);
  const restored=JSON.parse(fs.readFileSync(registryPath,'utf8')).domains['ai-providers'];
  assert.deepEqual(restored.active,before); assert.equal(restored.history.at(-1).type,'ROLLBACK');
  const repeat=rollbackReplacement({domain:'ai-providers',promotionHash:p.promotionHash,reason:'repeat',evidenceHash:d('f')});
  assert.equal(repeat.rolledBack,false); assert.equal(repeat.reasons.includes('PROMOTION_NOT_CURRENT'),true);
  const lockPath=registryPath+'.mutation.lock'; const lockBefore=fs.readFileSync(registryPath,'utf8'); fs.mkdirSync(lockPath);
  assert.throws(()=>promoteReplacement({domain:'ai-providers',proposal,challengerIdentity:challenger,certification}),/INCUMBENT_MUTATION_LOCK_TIMEOUT/);
  fs.rmSync(lockPath,{recursive:true,force:true}); assert.equal(fs.readFileSync(registryPath,'utf8'),lockBefore);
  const stableBefore=fs.readFileSync(registryPath,'utf8'); fs.writeFileSync(ledgerPath,'{corrupt\n');
  const blocked=promoteReplacement({domain:'ai-providers',proposal,challengerIdentity:challenger,certification});
  assert.equal(blocked.promoted,false); assert.equal(blocked.reasons.includes('EVIDENCE_LEDGER_INVALID'),true); assert.equal(fs.readFileSync(registryPath,'utf8'),stableBefore);
  console.log('INCUMBENT_PROMOTION_ROLLBACK_PASS');
} finally {
  fs.writeFileSync(registryPath,registryBackup);
  fs.rmSync(registryPath+'.mutation.lock',{recursive:true,force:true});
  if(ledgerBackup===null) fs.rmSync(ledgerPath,{force:true}); else fs.writeFileSync(ledgerPath,ledgerBackup);
}
