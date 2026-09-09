const uniq=xs=>[...new Set(xs)];
export function eligibleDeployRoutes(routes=[]){
  return routes.filter(r=>r?.enabled!==false&&r?.executionType==='remote'&&r?.zeroCostVerified===true&&r?.zeroMandatorySpend!==false&&Number(r?.unitCost||0)===0&&r?.billingRequired!==true);
}
export function deploymentMeshPlan({routes=[],criticalDomains=[]}={}){
  const eligible=eligibleDeployRoutes(routes),domains={};
  for(const domain of uniq(criticalDomains.map(String))){
    const matches=eligible.filter(r=>(r.domains||[]).includes(domain));
    domains[domain]={routes:matches.map(r=>r.id||r.providerId),count:matches.length,pass:matches.length>=2};
  }
  const blockers=Object.entries(domains).filter(([,v])=>!v.pass).map(([k])=>'route_redundancy:'+k);
  return {schema:'arbm-deployment-mesh-v1',state:blockers.length?'BLOCKED':'READY',eligible:eligible.map(r=>r.id||r.providerId),domains,blockers,zeroMandatorySpend:true};
}
export async function deployWithFailover(plan={},domain='',payload={},transport){
  if(plan.state!=='READY')throw new Error('deployment_mesh_not_ready');
  if(typeof transport!=='function')throw new Error('deployment_transport_required');
  const ids=plan.domains?.[domain]?.routes||[],errors=[];
  for(const id of ids){try{const out=await transport(id,payload);if(out?.state==='SUCCEEDED')return {state:'SUCCEEDED',routeId:id,failoverCount:errors.length,result:out};errors.push(id+':'+String(out?.state||'FAILED'));}catch(e){errors.push(id+':'+String(e?.message||e));}}
  return {state:'FAILED',errors};
}
