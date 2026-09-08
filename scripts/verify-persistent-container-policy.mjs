import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

const root=path.resolve(new URL('..',import.meta.url).pathname.replace(/^\/(?:[A-Za-z]:)/,m=>m.slice(1)));
const read=rel=>fs.readFileSync(path.join(root,rel),'utf8');
const agent=read('scripts/persistent-continuity-agent.mjs');
const attest=read('scripts/cloud-host-attestation.mjs');
const docker=read('Dockerfile');
const back=JSON.parse(read('cloud/back4app/deployment-contract.json'));
const claw=JSON.parse(read('cloud/clawcloud/deployment-contract.json'));

assert.match(agent,/clawcloud/);
assert.match(agent,/back4app/);
assert.match(agent,/benchmark/);
assert.ok(!/\['oci','gcp'\]/.test(agent),'OCI must not be active in persistent agent');
assert.match(attest,/v==='clawcloud'/);
assert.match(attest,/v==='back4app'/);
assert.doesNotMatch(attest,/v==='oci'/);

assert.match(docker,/USER node/);
assert.match(docker,/HEALTHCHECK/);
assert.match(docker,/persistent-container-health\.mjs/);
assert.ok(!/ARBM_HOST_TOKEN\s*=/.test(docker),'host token must never be baked into image');
assert.equal(back.providerId,'back4app-free-persistent');
assert.equal(back.cpuCoresMax,0.25);
assert.equal(back.memoryMiBMax,256);
assert.equal(back.costPolicy,'zero-spend-only');
assert.equal(back.activation,'fail-closed-until-independent-billing-verification');

assert.equal(claw.providerId,'clawcloud-free-persistent');
assert.equal(claw.cpuCoresMax,0.25);
assert.equal(claw.memoryMiBMax,1024);
assert.equal(claw.costPolicy,'zero-spend-only');
assert.equal(claw.activation,'fail-closed-until-independent-billing-verification');

const workflowDir=path.join(root,'.github','workflows');
for(const file of fs.readdirSync(workflowDir).filter(x=>x.endsWith('.yml')||x.endsWith('.yaml'))){
  const text=fs.readFileSync(path.join(workflowDir,file),'utf8');
  assert.ok(!/oci-always-free-persistent|arbm-oci-persistent|infra\/persistent\/oci|cloud\/oci\//i.test(text),`active workflow contains retired OCI path: ${file}`);
}

console.log(JSON.stringify({suite:'PERSISTENT_CONTAINER_POLICY',state:'PASS',benchmark:['clawcloud','back4app'],modal:'DISQUALIFIED_FINANCIAL',oci:'RETIRED'}));
