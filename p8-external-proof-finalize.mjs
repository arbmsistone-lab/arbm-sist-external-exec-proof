import {attestationFromEnvelope} from './p8-external-proof-attestor.mjs';
import {updateRegistry} from './incumbent-registry-updater.mjs';
const attestation=attestationFromEnvelope();
const update=updateRegistry(attestation,'ai-providers');
console.log(JSON.stringify({
  verified:attestation.verifiedCount,
  status:update.status,
  active:update.active,
  replacementSafe:update.usableForReplacementProposal,
  evidenceSequence:update.evidenceSequence,
  evidenceHash:update.evidenceHash
},null,2));
