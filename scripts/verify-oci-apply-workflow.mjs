import fs from 'node:fs';
const file=new URL('../.github/workflows/arbm-oci-persistent-apply.yml',import.meta.url).pathname.replace(/^\/(.:)/,'$1');
const s=fs.readFileSync(file,'utf8');
const need=[
  'workflow_dispatch:',
  'id-token: write',
  'ARBM_ZERO_SPEND_OCI_APPLY',
  'home_region_verified',
  'always_free_inventory_verified',
  'node scripts/terraform-state-session.mjs issue',
  'node scripts/verify-oci-zero-spend-plan.mjs',
  'terraform -chdir=infra/persistent/oci apply',
  'node scripts/terraform-state-session.mjs revoke'
];
for(const x of need)if(!s.includes(x))throw new Error(`workflow_requirement_missing:${x}`);
for(const forbidden of ['schedule:','pull_request:','terraform destroy','cancel-in-progress: true'])if(s.includes(forbidden))throw new Error(`workflow_forbidden:${forbidden}`);
if(/\npush:\s*$/m.test(s))throw new Error('automatic_push_trigger_forbidden');
const issue=s.indexOf('terraform-state-session.mjs issue');
const plan=s.indexOf('verify-oci-zero-spend-plan.mjs');
const apply=s.indexOf('terraform -chdir=infra/persistent/oci apply');
const revoke=s.indexOf('terraform-state-session.mjs revoke');
if(!(issue<plan&&plan<apply&&apply<revoke))throw new Error('workflow_gate_order_invalid');
console.log(JSON.stringify({suite:'OCI_APPLY_WORKFLOW_POLICY',state:'PASS',manualOnly:true,ephemeralStateSession:true}));