import fs from 'node:fs';
import assert from 'node:assert/strict';
import {promoteReplacement,rollbackReplacement} from './incumbent-promotion-controller.mjs';
import {evaluateReplacementProposal} from './replacement-proposal-gate.mjs';
import {appendEvidence} from './universal-radar-evidence-ledger.mjs';
import {certifyReplacement} from './replacement-certification.mjs';
const registryPath='incumbent-registry.json',ledgerPath='universal-radar-evidence-ledger.jsonl',queuePath='replacement-proposals.json';
const registryBackup=fs.readFileSync(registryPath,'utf8'),ledgerBackup=fs.existsSync(ledgerPath)?fs.readFileSync(ledgerPath,'utf8'):null,queueBackup=fs.existsSync(queuePath)?fs.readFileSync(queuePath,'utf8'):null;
const d=c=>'sha256:'+c.repeat(64), result={grade:'replacementGrade',decision:'REPLACEMENT_CANDIDATE',replacementApplied:false,gates:{sampleOk:true,pairedOk:true,integrityOk:true}};
function certifiedProposal(challenger){
 const proposal=evaluateReplacementProposal({domain:'ai-providers',challengerResult:result,challengerIdentity:challenger});
 fs.writeFileSync(queuePath,JSON.stringify({schema:'arbm-replacement-proposals-v1',items:[{proposalHash:proposal.proposalHash,status:'PENDING_P9'}]},null,2));
 const src=appendEvidence({type:'REPLACEMENT_VALIDATION',status:'PASS',rollbackReady:true,domain:'ai-providers',proposalHash:proposal.proposalHash,challengerArtifactSha256:challenger.artifactSha256});
 const certification=certifyReplacement({proposal,certificationResult:{status:'PASS',rollbackReady:true,evidenceHash:src.entryHash}});
 assert.equal(certification.certified,true); return {proposal,certification};
}
try{
 const before=JSON.parse(registryBackup).domains['ai-providers'].active;
 const challenger={id:'candidate-x',version:'2',artifactSha256:d('b'),activatedAt:'2026-09-08T16:00:00Z',zeroSpendVerified:true};
 const {proposal,certification}=certifiedProposal(challenger);
 const forged={status:'PASS',rollbackReady:true,evidenceHash:d('d')};
 assert.equal(promoteReplacement({domain:'ai-providers',proposal,challengerIdentity:challenger,certification:forged}).reasons.includes('CERTIFICATION_EVIDENCE_MISMATCH'),true);
 const tampered=promoteReplacement({domain:'ai-providers',proposal:{...proposal,domain:'coding-models'},challengerIdentity:challenger,certification});
 assert.equal(tampered.promoted,false); assert.equal(tampered.reasons.includes('PROPOSAL_HASH_MISMATCH'),true);
 const p=promoteReplacement({domain:'ai-providers',proposal,challengerIdentity:challenger,certification}); assert.equal(p.promoted,true);
 const rb=rollbackReplacement({domain:'ai-providers',promotionHash:p.promotionHash,reason:'canary regression',evidenceHash:d('e')}); assert.equal(rb.rolledBack,true);
 assert.deepEqual(JSON.parse(fs.readFileSync(registryPath,'utf8')).domains['ai-providers'].active,before);
 const replay=promoteReplacement({domain:'ai-providers',proposal,challengerIdentity:challenger,certification}); assert.equal(replay.promoted,false); assert.equal(replay.reasons.includes('PROPOSAL_ALREADY_USED'),true);
 const challenger2={id:'candidate-y',version:'3',artifactSha256:d('c'),activatedAt:'2026-09-08T16:10:00Z',zeroSpendVerified:true};
 const second=certifiedProposal(challenger2); const lockPath=registryPath+'.mutation.lock'; const lockBefore=fs.readFileSync(registryPath,'utf8'); fs.mkdirSync(lockPath);
 assert.throws(()=>promoteReplacement({domain:'ai-providers',proposal:second.proposal,challengerIdentity:challenger2,certification:second.certification}),/FILE_MUTATION_LOCK_TIMEOUT/);
 fs.rmSync(lockPath,{recursive:true,force:true}); assert.equal(fs.readFileSync(registryPath,'utf8'),lockBefore);
 fs.mkdirSync(lockPath); const old=new Date(Date.now()-700000); fs.utimesSync(lockPath,old,old);
 const recovered=promoteReplacement({domain:'ai-providers',proposal:second.proposal,challengerIdentity:challenger2,certification:second.certification}); assert.equal(recovered.promoted,true);
 const recoveredRb=rollbackReplacement({domain:'ai-providers',promotionHash:recovered.promotionHash,reason:'stale lock recovery',evidenceHash:d('9')}); assert.equal(recoveredRb.rolledBack,true);
 const stableBefore=fs.readFileSync(registryPath,'utf8'); fs.writeFileSync(ledgerPath,'{corrupt\n');
 const blocked=promoteReplacement({domain:'ai-providers',proposal:second.proposal,challengerIdentity:challenger2,certification:second.certification});
 assert.equal(blocked.promoted,false); assert.equal(blocked.reasons.includes('EVIDENCE_LEDGER_INVALID'),true); assert.equal(fs.readFileSync(registryPath,'utf8'),stableBefore);
 console.log('INCUMBENT_PROMOTION_ROLLBACK_PASS');
} finally {
 fs.writeFileSync(registryPath,registryBackup); fs.rmSync(registryPath+'.mutation.lock',{recursive:true,force:true});
 if(ledgerBackup===null)fs.rmSync(ledgerPath,{force:true});else fs.writeFileSync(ledgerPath,ledgerBackup);
 if(queueBackup===null)fs.rmSync(queuePath,{force:true});else fs.writeFileSync(queuePath,queueBackup);
}
