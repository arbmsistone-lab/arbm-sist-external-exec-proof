import fs from 'node:fs';
const file=process.argv[2];if(!file)throw new Error('plan_json_path_required');
const raw=fs.readFileSync(file,'utf8').replace(/^\\uFEFF/,'');
const plan=JSON.parse(raw);
const changes=Array.isArray(plan.resource_changes)?plan.resource_changes:[];
const managed=changes.filter(x=>x.mode==='managed');
const mutations=managed.filter(x=>!['no-op','read'].includes(String(x.change?.actions?.[0]||'')));
for(const r of mutations){
  const actions=r.change?.actions||[];
  if(r.address!=='oci_core_instance.arbm_persistent')throw new Error(`unexpected_resource_change:${r.address}`);
  if(actions.length!==1||actions[0]!=='create')throw new Error(`unsafe_actions:${r.address}:${actions.join(',')}`);
}
if(mutations.length>1)throw new Error(`too_many_mutations:${mutations.length}`);
if(mutations.length===1){
  const after=mutations[0].change?.after||{};
  const shape=String(after.shape||'');
  if(!['VM.Standard.A1.Flex','VM.Standard.E2.1.Micro'].includes(shape))throw new Error(`non_free_shape:${shape}`);
  if(shape==='VM.Standard.A1.Flex'){
    const cfg=Array.isArray(after.shape_config)?after.shape_config[0]||{}:{};
    const ocpus=Number(cfg.ocpus||0),mem=Number(cfg.memory_in_gbs||0);
    if(!(ocpus>0&&ocpus<=2&&mem>0&&mem<=12))throw new Error(`a1_ceiling_exceeded:${ocpus}:${mem}`);
  }
  if(after.freeform_tags?.['ARBM-CostPolicy']!=='zero-spend-only')throw new Error('zero_spend_tag_missing');
}
console.log(JSON.stringify({suite:'OCI_ZERO_SPEND_PLAN_POLICY',state:'PASS',mutations:mutations.length,mode:mutations.length?'create-one':'no-op'}));