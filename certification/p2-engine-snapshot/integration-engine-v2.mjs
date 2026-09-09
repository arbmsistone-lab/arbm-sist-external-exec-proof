export async function invokeIntegrationWithFailover(engine,{type='',capability='',payload={}}={},transport){
 if(!engine?.resolve||!engine?.invoke)throw new Error('integration_engine_required');if(typeof transport!=='function')throw new Error('transport_required');
 const routes=engine.resolve({type,capability}),errors=[];if(!routes.length)return {state:'BLOCKED',reason:'no_integration_route',errors};
 for(const route of routes){try{const out=await engine.invoke(route.id,payload,{transport});if(out.state==='SUCCEEDED')return {...out,state:'SUCCEEDED',failoverCount:errors.length};errors.push(route.id+':'+out.state);}catch(e){errors.push(route.id+':'+String(e?.message||e));}}
 return {state:'FAILED',errors,failoverCount:errors.length};
}
export function integrationV2Gate(engine){const types=new Set([...(engine?.routes?.values?.()||[])].filter(r=>r.enabled&&r.zeroMandatorySpend===true).map(r=>r.type));const missing=['mcp','api','webhook','connector'].filter(x=>!types.has(x));return {pass:missing.length===0,missing,types:[...types]};}
