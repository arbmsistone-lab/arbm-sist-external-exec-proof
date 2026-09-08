import {discoverIncumbents} from './incumbent-discovery.mjs';
import {attestDiscovery} from './incumbent-attestor.mjs';
import {updateRegistry} from './incumbent-registry-updater.mjs';
const discovery=discoverIncumbents();
const attestation=attestDiscovery(discovery);
const update=updateRegistry(attestation,'ai-providers');
console.log(JSON.stringify({
  configured:attestation.configuredCount,
  verified:attestation.verifiedCount,
  routes:attestation.routes.map(x=>({id:x.id,configured:x.configured,state:x.state,reasons:x.reasons})),
  registry:update.status,
  replacementSafe:update.usableForReplacementProposal,
  evidenceSequence:update.evidenceSequence
},null,2));
