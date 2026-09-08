import fs from 'node:fs';
import {appendEvidence,verifyLedger,findEvidence,validLedgerHash} from './universal-radar-evidence-ledger.mjs';
import {digest,validProposalHash} from './proposal-integrity.mjs';
const queuePath='replacement-proposals.json';
const loadQueue=()=>fs.existsSync(queuePath)?JSON.parse(fs.readFileSync(queuePath,'utf8')):{items:[]};
export function certifyReplacement({proposal,certificationResult}){
  const reasons=[]; const q=loadQueue();
  if(!proposal?.approved||!validProposalHash(proposal)) reasons.push('PROPOSAL_INVALID');
  const queued=q.items?.find(x=>x.proposalHash===proposal?.proposalHash&&x.status==='PENDING_P9');
  if(!queued) reasons.push('PROPOSAL_NOT_QUEUED');
  if(certificationResult?.status!=='PASS'||certificationResult?.rollbackReady!==true) reasons.push('CERTIFICATION_RESULT_INCOMPLETE');
  if(!validLedgerHash(certificationResult?.evidenceHash)) reasons.push('CERTIFICATION_SOURCE_HASH_INVALID');
  const source=findEvidence(certificationResult?.evidenceHash); const sourcePayload=source?.entry?.payload;
  if(!source.ok||sourcePayload?.type!=='REPLACEMENT_VALIDATION'||sourcePayload?.status!=='PASS'||sourcePayload?.rollbackReady!==true||sourcePayload?.domain!==proposal?.domain||sourcePayload?.proposalHash!==proposal?.proposalHash||sourcePayload?.challengerArtifactSha256!==proposal?.challengerIdentity?.artifactSha256) reasons.push('CERTIFICATION_SOURCE_MISMATCH');
  const ledger=verifyLedger(); if(!ledger.ok) reasons.push('EVIDENCE_LEDGER_INVALID');
  if(reasons.length) return {certified:false,reasons};
  const payload={type:'REPLACEMENT_CERTIFIED',domain:proposal.domain,proposalHash:proposal.proposalHash,challengerArtifactSha256:proposal.challengerIdentity.artifactSha256,certificationSourceHash:certificationResult.evidenceHash,rollbackReady:true,status:'PASS'};
  const entry=appendEvidence(payload);
  return {certified:true,status:'PASS',rollbackReady:true,evidenceHash:entry.entryHash,proposalHash:proposal.proposalHash,domain:proposal.domain,challengerArtifactSha256:proposal.challengerIdentity.artifactSha256};
}
