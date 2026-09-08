import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
const validator=new URL('./verify-oci-zero-spend-plan.mjs',import.meta.url).pathname.replace(/^\/(.:)/,'$1');
function run(plan){
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'arbm-plan-'));
  const file=path.join(dir,'plan.json');
  try{
    fs.writeFileSync(file,JSON.stringify(plan));
    return spawnSync(process.execPath,[validator,file],{encoding:'utf8'});
  }finally{
    fs.rmSync(dir,{recursive:true,force:true});
  }
}
const base={address:'oci_core_instance.arbm_persistent',mode:'managed',change:{actions:['create'],after:{shape:'VM.Standard.A1.Flex',shape_config:[{ocpus:1,memory_in_gbs:6}],freeform_tags:{'ARBM-CostPolicy':'zero-spend-only'}}}};
assert.equal(run({resource_changes:[base]}).status,0);
assert.equal(run({resource_changes:[{...base,change:{...base.change,actions:['no-op']}}]}).status,0);
for(const actions of [['delete'],['update'],['delete','create']]){
  assert.notEqual(run({resource_changes:[{...base,change:{...base.change,actions}}]}).status,0);
}
const extra={address:'oci_core_vcn.extra',mode:'managed',change:{actions:['create'],after:{}}};
assert.notEqual(run({resource_changes:[base,extra]}).status,0);
const tooBig={...base,change:{...base.change,after:{...base.change.after,shape_config:[{ocpus:3,memory_in_gbs:18}]}}};
assert.notEqual(run({resource_changes:[tooBig]}).status,0);
const wrongShape={...base,change:{...base.change,after:{...base.change.after,shape:'VM.Standard.E4.Flex'}}};
assert.notEqual(run({resource_changes:[wrongShape]}).status,0);
const noTag={...base,change:{...base.change,after:{...base.change.after,freeform_tags:{}}}};
assert.notEqual(run({resource_changes:[noTag]}).status,0);
console.log(JSON.stringify({suite:'OCI_ZERO_SPEND_PLAN_POLICY_TEST',state:'PASS',cases:9}));