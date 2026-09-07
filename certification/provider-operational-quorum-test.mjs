import assert from 'node:assert/strict';
import {execFileSync,spawnSync} from 'node:child_process';
const out=execFileSync(process.execPath,['certification/provider-operational-quorum.mjs'],{encoding:'utf8'});
const r=JSON.parse(out);
assert.equal(r.failClosed,true);
assert.equal(r.requiredIndependentDomains,3);
assert.equal(r.activeIndependentDomains,2);
assert.deepEqual(new Set(r.activeDomains),new Set(['github','gitlab']));
assert.equal(r.pass,false);
assert.equal(r.invalidActive.length,0);
assert.ok(r.preparedNotLive.includes('oci-always-free-persistent'));
const enforced=spawnSync(process.execPath,['certification/provider-operational-quorum.mjs'],{
  encoding:'utf8',env:{...process.env,ARBM_ENFORCE_PROVIDER_QUORUM:'1'}
});
assert.notEqual(enforced.status,0);
console.log('PROVIDER_OPERATIONAL_QUORUM_TEST_PASS');
