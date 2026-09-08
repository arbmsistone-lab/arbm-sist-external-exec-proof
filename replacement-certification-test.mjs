import fs from 'node:fs';
import assert from 'node:assert/strict';
import {appendEvidence} from './universal-radar-evidence-ledger.mjs';
import {certifyReplacement} from './replacement-certification.mjs';
import {evaluateReplacementProposal} from './replacement-proposal-gate.mjs';
const regPath='incumbent-registry.json',qPath='replacement-proposals.json',ledgerPath='universal-radar-evidence-ledger.jsonl';
const regBackup=fs.readFileSync(regPath,'utf8'),qBackup=fs.existsSync(qPath)?fs.readFileSync(qPath,'utf8'):null,ledgerBackup=fs.existsSync(ledgerPath)?fs.readFileSync(ledgerPath,'utf8'):null;
try{
 const challenger={id:'candidate-x',version:'2',artifactSha256:'sha256:'+'b'.repeat(64),activatedAt:'2026-09-08T16:00:00Z',zeroSpendVerified:true};
 const result={grade:'replacementGrade',decision:'REPLACEMENT_CANDIDATE',replacementApplied:false,gates:{sampleOk:true,pairedOk:true,integrityOk:true}};
 const proposal=evaluateReplacementProposal({domain:'ai-providers',challengerResult:result,challengerIdentity:challenger});
 fs.writeFileSync(qPath,JSON.stringify({schema:'arbm-replacement-proposals-v1',items:[{proposalHash:proposal.proposalHash,status:'PENDING_P9'}]},null,2));
 const fake=certifyReplacement({proposal,certificationResult:{status:'PASS',rollbackReady:true,evidenceHash:'sha256:'+'d'.repeat(64)}});
 assert.equal(fake.certified,false); assert.equal(fake.reasons.includes('CERTIFICATION_SOURCE_MISMATCH'),true);
 const wrong=appendEvidence({type:'REPLACEMENT_VALIDATION',status:'PASS',rollbackReady:true,domain:'ai-providers',proposalHash:'sha256:'+'e'.repeat(64),challengerArtifactSha256:challenger.artifactSha256});
 const wrongCert=certifyReplacement({proposal,certificationResult:{status:'PASS',rollbackReady:true,evidenceHash:wrong.entryHash}});
 assert.equal(wrongCert.certified,false); assert.equal(wrongCert.reasons.includes('CERTIFICATION_SOURCE_MISMATCH'),true);
 const src=appendEvidence({type:'REPLACEMENT_VALIDATION',status:'PASS',rollbackReady:true,domain:'ai-providers',proposalHash:proposal.proposalHash,challengerArtifactSha256:challenger.artifactSha256});
 const cert=certifyReplacement({proposal,certificationResult:{status:'PASS',rollbackReady:true,evidenceHash:src.entryHash}});
 assert.equal(cert.certified,true); assert.equal(cert.proposalHash,proposal.proposalHash);
 console.log('REPLACEMENT_CERTIFICATION_PASS');
} finally {fs.writeFileSync(regPath,regBackup);if(qBackup===null)fs.rmSync(qPath,{force:true});else fs.writeFileSync(qPath,qBackup);if(ledgerBackup===null)fs.rmSync(ledgerPath,{force:true});else fs.writeFileSync(ledgerPath,ledgerBackup);}
