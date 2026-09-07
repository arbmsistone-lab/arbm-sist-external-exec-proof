import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';

const root=path.resolve(new URL('..',import.meta.url).pathname.replace(/^\/(?:[A-Za-z]:)/,m=>m.slice(1)));
const read=rel=>fs.readFileSync(path.join(root,rel),'utf8');
const versions=read('infra/persistent/oci/versions.tf');
const vars=read('infra/persistent/oci/variables.tf');
const main=read('infra/persistent/oci/main.tf');
const bootstrap=read('cloud/common/bootstrap-persistent-host.sh');
const blocked=read('infra/persistent/gcp/BLOCKED.md');

assert.match(versions,/required_version\s*=\s*"= 1\.16\.1"/);
assert.match(versions,/source\s*=\s*"oracle\/oci"/);
assert.match(versions,/version\s*=\s*"= 8\.29\.0"/);
assert.match(vars,/var\.ocpus > 0 && var\.ocpus <= 2/);
assert.match(vars,/var\.memory_in_gbs > 0 && var\.memory_in_gbs <= 12/);
assert.match(main,/var\.apply_guard == "ARBM_ZERO_SPEND_OCI_APPLY"/);
assert.match(main,/var\.home_region_verified/);
assert.match(main,/var\.always_free_inventory_verified/);
assert.match(main,/assign_public_ip\s*=\s*true/);
assert.ok(!/ARBM_HOST_TOKEN/.test(versions+vars+main),'secret token must not enter Terraform state');

assert.match(bootstrap,/ARBM_HOST_TOKEN_FILE/);
assert.ok(!/zeroSpendVerified\s*=\s*1/.test(bootstrap),'bootstrap must not self-approve cost');
assert.match(blocked,/intentionally contains no deployable Terraform configuration/);

const gcpDir=path.join(root,'infra/persistent/gcp');
const gcpTf=fs.readdirSync(gcpDir).filter(x=>x.endsWith('.tf'));
assert.deepEqual(gcpTf,[],'GCP deployable Terraform must stay absent while zero-cost networking is unproven');

for(const rel of ['infra/persistent/oci/terraform.tfvars.example']){
  const text=read(rel);
  assert.ok(!/ARBM_ZERO_SPEND_OCI_APPLY/.test(text),'example must remain blocked');
  assert.match(text,/apply_guard\s*=\s*"BLOCKED"/);
  assert.match(text,/home_region_verified\s*=\s*false/);
  assert.match(text,/always_free_inventory_verified\s*=\s*false/);
}
console.log(JSON.stringify({suite:'PERSISTENT_IAC_POLICY',state:'PASS',ociCeiling:'2 OCPU / 12 GB',gcp:'BLOCKED_ZERO_COST_NETWORK'}));
