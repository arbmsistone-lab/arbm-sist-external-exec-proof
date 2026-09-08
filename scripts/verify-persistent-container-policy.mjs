import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

const root=path.resolve(new URL('..',import.meta.url).pathname.replace(/^\/(?:[A-Za-z]:)/,m=>m.slice(1)));
const read=rel=>fs.readFileSync(path.join(root,rel),'utf8');
const agent=read('scripts/persistent-continuity-agent.mjs');
const attest=read('scripts/cloud-host-attestation.mjs');
const docker=read('Dockerfile');
const modal=read('cloud/modal/app.py');
const back=JSON.parse(read('cloud/back4app/deployment-contract.json'));

assert.match(agent,/\['modal','back4app','gcp'\]/);
assert.ok(!/\['oci','gcp'\]/.test(agent),'OCI must not be active in persistent agent');
assert.match(attest,/v==='modal'/);
assert.match(attest,/v==='back4app'/);
assert.doesNotMatch(attest,/v==='oci'/);

assert.match(docker,/USER node/);
assert.match(docker,/HEALTHCHECK/);
assert.match(docker,/persistent-container-health\.mjs/);
assert.ok(!/ARBM_HOST_TOKEN\s*=/.test(docker),'host token must never be baked into image');

assert.match(modal,/ARBM_CLOUD_VENDOR": "modal"/);
assert.match(modal,/ARBM_HOST_ID": "modal-starter-persistent"/);
assert.match(modal,/cpu=\(0\.125, 0\.125\)/);
assert.match(modal,/memory=\(512, 512\)/);
assert.match(modal,/min_containers=1/);
assert.match(modal,/max_containers=1/);

assert.equal(back.providerId,'back4app-free-persistent');
assert.equal(back.cpuCoresMax,0.25);
assert.equal(back.memoryMiBMax,256);
assert.equal(back.costPolicy,'zero-spend-only');
assert.equal(back.activation,'fail-closed-until-independent-billing-verification');

const workflowDir=path.join(root,'.github','workflows');
for(const file of fs.readdirSync(workflowDir).filter(x=>x.endsWith('.yml')||x.endsWith('.yaml'))){
  const text=fs.readFileSync(path.join(workflowDir,file),'utf8');
  assert.ok(!/oci-always-free-persistent|arbm-oci-persistent|infra\/persistent\/oci|cloud\/oci\//i.test(text),`active workflow contains retired OCI path: ${file}`);
}

console.log(JSON.stringify({suite:'PERSISTENT_CONTAINER_POLICY',state:'PASS',primary:'modal',secondary:'back4app',oci:'RETIRED'}));
