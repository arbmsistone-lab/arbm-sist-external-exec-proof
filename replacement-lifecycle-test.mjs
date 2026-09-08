import fs from 'node:fs';
import assert from 'node:assert/strict';
import {submitReplacementProposal} from './replacement-proposal-queue.mjs';
import {certifyReplacement} from './replacement-certification.mjs';
import {promoteReplacement,rollbackReplacement} from './incumbent-promotion-controller.mjs';
import {registerRollbackValidation} from './rollback-validation.mjs';
import {appendEvidence} from './universal-radar-evidence-ledger.mjs';
import {reconcileQueue} from './replacement-lifecycle.mjs';
const regPath='incumbent-registry.json',qPath='replacement-proposals.json',ledgerPath='universal-radar-evidence-ledger.jsonl';
const regBackup=fs.readFileSync(regPath,'utf8'),qBackup=fs.existsSync(qPath)?fs.readFileSync(qPath,'utf8'):null,ledgerBackup=fs.existsSync(ledgerPath)?fs.readFileSync(ledgerPath,'utf8'):null;
const d=c=>'sha256:'+c.repeat(64);
try{
 const challenger={id:'life-x',version:'1',artifactSha256:d('7'),activatedAt:'2026-09-08T17:00:00Z',zeroSpendVerified:true};
 const result={grade:'replacementGrade',decision:'REPLACEMENT_CANDIDATE',replacementApplied:false,gates:{sampleOk:true,pairedOk:true,integrityOk:true}};
 const queued=submitReplacementProposal({domain:'ai-providers',challengerResult:result,challengerIdentity:challenger}); assert.equal(queued.queued,true);
 let q=JSON.parse(fs.readFileSync(qPath,'utf8')); assert.equal(q.items.find(x=>x.proposalHash===queued.gate.proposalHash).status,'PENDING_P9');
 const src=appendEvidence({type:'REPLACEMENT_VALIDATION',status:'PASS',rollbackReady:true,domain:'ai-providers',proposalHash:queued.gate.proposalHash,challengerArtifactSha256:challenger.artifactSha256});
 const cert=certifyReplacement({proposal:queued.gate,certificationResult:{status:'PASS',rollbackReady:true,evidenceHash:src.entryHash}}); assert.equal(cert.certified,true);
 reconcileQueue(); q=JSON.parse(fs.readFileSync(qPath,'utf8')); assert.equal(q.items.find(x=>x.proposalHash===queued.gate.proposalHash).status,'CERTIFIED');
 const promoted=promoteReplacement({domain:'ai-providers',proposal:queued.gate,challengerIdentity:challenger,certification:cert}); assert.equal(promoted.promoted,true);
 reconcileQueue(); q=JSON.parse(fs.readFileSync(qPath,'utf8')); assert.equal(q.items.find(x=>x.proposalHash===queued.gate.proposalHash).status,'PROMOTED');
 const forged=rollbackReplacement({domain:'ai-providers',promotionHash:promoted.promotionHash,reason:'forged',evidenceHash:d('8')}); assert.equal(forged.rolledBack,false); assert.equal(forged.reasons.includes('ROLLBACK_EVIDENCE_MISMATCH'),true);
 const rbSrc=appendEvidence({type:'ROLLBACK_VALIDATION_SOURCE',status:'PASS',domain:'ai-providers',promotionHash:promoted.promotionHash});
 const rbProof=registerRollbackValidation({domain:'ai-providers',promotionHash:promoted.promotionHash,reason:'lifecycle regression',validationResult:{status:'PASS',evidenceHash:rbSrc.entryHash}}); assert.equal(rbProof.validated,true);
 const rolled=rollbackReplacement({domain:'ai-providers',promotionHash:promoted.promotionHash,reason:'lifecycle regression',evidenceHash:rbProof.evidenceHash}); assert.equal(rolled.rolledBack,true);
 reconcileQueue(); q=JSON.parse(fs.readFileSync(qPath,'utf8')); assert.equal(q.items.find(x=>x.proposalHash===queued.gate.proposalHash).status,'ROLLED_BACK');
 console.log('REPLACEMENT_LIFECYCLE_PASS');
} finally {
 fs.writeFileSync(regPath,regBackup);
 if(qBackup===null)fs.rmSync(qPath,{force:true});else fs.writeFileSync(qPath,qBackup);
 if(ledgerBackup===null)fs.rmSync(ledgerPath,{force:true});else fs.writeFileSync(ledgerPath,ledgerBackup);
}
