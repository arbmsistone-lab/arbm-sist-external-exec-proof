import fs from 'node:fs';
const req=JSON.parse(fs.readFileSync('certification/benchmark-capability-requirements.json','utf8').replace(/^\uFEFF/,''));
const providers=JSON.parse(fs.readFileSync('certification/provider-capabilities.json','utf8').replace(/^\uFEFF/,''));
const results={};
for(const [family,r] of Object.entries(req.families)){
  results[family]=[];
  for(const p of providers.providers){
    const reasons=[];
    if(p.state!=='ACTIVE') reasons.push('provider_not_active');
    if(!p.zeroCostVerified) reasons.push('zero_cost_not_verified');
    for(const k of ['cpu','memoryMB','diskMB','gpu','maxTaskSeconds']) if(r[k]!=null && (p[k]??0)<r[k]) reasons.push(`${k}_insufficient`);
    for(const k of ['docker','kvm']) if(r[k]===true && p[k]!==true) reasons.push(`${k}_missing`);
    if(r.requiresAuthorizedDataset===true && p.authorizedDataset!==true) reasons.push('authorized_dataset_missing');
    results[family].push({provider:p.id,eligible:reasons.length===0,reasons});
  }
}
console.log(JSON.stringify({schema:'arbm-capability-match-v1',failClosed:true,results},null,2));
