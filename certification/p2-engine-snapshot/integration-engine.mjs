const TYPES=new Set(['mcp','api','webhook','connector']);
export class IntegrationEngine{
  constructor(){this.routes=new Map();}
  register(route={}){const id=String(route.id||''),type=String(route.type||'');if(!id||!TYPES.has(type))throw new Error('integration_route_invalid');if(route.zeroMandatorySpend!==true)throw new Error('integration_not_free_verified');const row={...route,id,type,enabled:route.enabled!==false};this.routes.set(id,row);return {...row};}
  resolve({type='',capability=''}={}){return [...this.routes.values()].filter(r=>r.enabled&&(!type||r.type===type)&&(!capability||(r.capabilities||[]).includes(capability)));}
  async invoke(id,payload,{transport}={}){const route=this.routes.get(String(id));if(!route?.enabled)throw new Error('integration_route_unavailable');if(typeof transport!=='function')throw new Error('transport_required');const result=await transport(route,payload);return {routeId:route.id,type:route.type,state:result?.state||'SUCCEEDED',result};}
}
export function integrationGate(engine={}){const rows=[...(engine.routes?.values?.()||[])];const types=new Set(rows.map(x=>x.type));return {pass:['mcp','api','webhook','connector'].every(x=>types.has(x)),routes:rows.length,types:[...types]};}
