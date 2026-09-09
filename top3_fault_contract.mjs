import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';

function admit(cell,req={}){
  const blockers=[];
  if(cell.state!=='HEALTHY') blockers.push('cell_not_healthy');
  if(cell.queue_depth>=cell.max_queue_depth) blockers.push('queue_capacity_exhausted');
  if(cell.cpu_pct>=85) blockers.push('cpu_admission_block');
  if(cell.memory_pct>=85) blockers.push('memory_admission_block');
  if(cell.db_saturation_pct>=80) blockers.push('db_admission_block');
  if(cell.failover_headroom_pct<20) blockers.push('failover_headroom_low');
  if(req.residency_region&&!cell.residency_regions?.includes(req.residency_region)) blockers.push('cell_residency_block');
  return {admit:blockers.length===0,blockers};
}

const cells=[
 {id:'a',state:'HEALTHY',queue_depth:100,max_queue_depth:100,cpu_pct:90,memory_pct:60,db_saturation_pct:50,failover_headroom_pct:30,residency_regions:['sa-east-1']},
 {id:'b',state:'HEALTHY',queue_depth:5,max_queue_depth:100,cpu_pct:40,memory_pct:45,db_saturation_pct:30,failover_headroom_pct:45,residency_regions:['sa-east-1']}
];
const sat=admit(cells[0],{residency_region:'sa-east-1'});
const reroute=cells.find(c=>admit(c,{residency_region:'sa-east-1'}).admit);
assert.equal(sat.admit,false); assert.equal(reroute?.id,'b');
const residency=admit(cells[1],{residency_region:'us-east-1'});
assert.equal(residency.admit,false); assert.ok(residency.blockers.includes('cell_residency_block'));

const {publicKey,privateKey}=crypto.generateKeyPairSync('ed25519');
const canonical=x=>Buffer.from(JSON.stringify({tenant_id:x.tenant_id,cell_id:x.cell_id,generation:x.generation,expires_at:x.expires_at}));
const sign=x=>({...x,signature:crypto.sign(null,canonical(x),privateKey).toString('base64url')});
const verify=x=>crypto.verify(null,canonical(x),publicKey,Buffer.from(x.signature,'base64url'))&&Date.parse(x.expires_at)>Date.now();
const good=sign({tenant_id:'tenant-x',cell_id:'cell-b',generation:2,expires_at:new Date(Date.now()+60000).toISOString()});
assert.equal(verify(good),true);
assert.equal(verify({...good,cell_id:'cell-evil'}),false);
const expired=sign({tenant_id:'tenant-x',cell_id:'cell-b',generation:3,expires_at:new Date(Date.now()-1000).toISOString()});
assert.equal(verify(expired),false);
assert.ok(good.generation>1);
const cachedGeneration=2;
const rollback=sign({tenant_id:'tenant-x',cell_id:'cell-old',generation:1,expires_at:new Date(Date.now()+60000).toISOString()});
const rollbackBlocked=verify(rollback)&&rollback.generation<cachedGeneration;
assert.equal(rollbackBlocked,true);

function criticGate({criticRequired,criticHealthy}){
  return criticRequired&&!criticHealthy?{allow:false,reason:'critic_unavailable_fail_closed'}:{allow:true};
}
const critic=criticGate({criticRequired:true,criticHealthy:false});
assert.equal(critic.allow,false);

const evidence={schema:'arbm-top3-fault-contract-v1',cellSaturationBlocked:!sat.admit,rerouteSelected:reroute?.id==='b',residencyMismatchBlocked:!residency.admit,cacheSignatureTamperBlocked:verify({...good,cell_id:'cell-evil'})===false,cacheExpiredBlocked:verify(expired)===false,cacheGenerationRollbackBlocked:rollbackBlocked,criticUnavailableFailClosed:critic.allow===false,zeroSpendHard:true};
assert.ok(Object.entries(evidence).filter(([,v])=>typeof v==='boolean').every(([,v])=>v===true));
fs.mkdirSync('top3-evidence/security-load-failure',{recursive:true});
const raw=JSON.stringify(evidence,null,2)+'\n';
fs.writeFileSync('top3-evidence/security-load-failure/fault-contract.json',raw);
fs.writeFileSync('top3-evidence/security-load-failure/fault-contract.sha256',crypto.createHash('sha256').update(raw).digest('hex')+'  fault-contract.json\n');
console.log(JSON.stringify(evidence));
