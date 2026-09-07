import assert from 'node:assert/strict';
import {execFileSync,spawnSync} from 'node:child_process';
const out=execFileSync(process.execPath,['certification/global-release-gate.mjs'],{encoding:'utf8'});
const r=JSON.parse(out);
assert.equal(r.failClosed,true);
assert.equal(r.pass,false);
assert.ok(!r.blockers.some(x=>x.startsWith('providerOperationalQuorum:')));
assert.equal(r.providerQuorum.activeIndependentDomains,3);
assert.equal(r.providerQuorum.pass,true);
assert.ok(r.blockers.includes('osworldV2Content:BLOCKED_EXTERNAL_AUTH'));
assert.ok(r.blockers.includes('swefficiency:BLOCKED_EXTERNAL_COMPUTE'));
assert.ok(r.blockers.includes('terminalBench4:BLOCKED_EXTERNAL_COMPUTE'));
assert.ok(!r.blockers.some(x=>x.startsWith('p9DubboM0031:')));
const enforced=spawnSync(process.execPath,['certification/global-release-gate.mjs'],{
  encoding:'utf8',env:{...process.env,ARBM_ENFORCE_GLOBAL_RELEASE:'1'}
});
assert.notEqual(enforced.status,0);
console.log('GLOBAL_RELEASE_GATE_TEST_PASS');
