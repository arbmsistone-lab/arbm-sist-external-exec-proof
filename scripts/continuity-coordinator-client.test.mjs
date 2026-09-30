import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createCoordinatorClient} from './continuity-coordinator-client.mjs';
import {executePayloadSupervised} from './continuity-execution-supervisor.mjs';

const initial='initial-secret-sentinel',credential='request-secret-sentinel',fresh='fresh-secret-sentinel';
const env={ACTIONS_ID_TOKEN_REQUEST_URL:'https://oidc.example/token?job=1&audience=old',ACTIONS_ID_TOKEN_REQUEST_TOKEN:credential};
const url='https://coordinator.example';
const response=(status,body)=>new Response(JSON.stringify(body),{status});
const root=fs.mkdtempSync(path.join(os.tmpdir(),'arbm-oidc-long-'));
const runner=path.join(root,'child.mjs');
fs.writeFileSync(runner,`import fs from 'node:fs';import path from 'node:path';
const root=process.env.ARBM_RUN_ROOT;
for(const k of ['ARBM_OIDC','ACTIONS_ID_TOKEN_REQUEST_TOKEN','ACTIONS_ID_TOKEN_REQUEST_URL'])if(process.env[k])throw new Error('credential_in_child');
fs.writeFileSync(path.join(root,'started'),String(process.pid));
const deadline=Date.now()+3000;
while(!fs.existsSync(path.join(root,'released'))){if(Date.now()>deadline)throw new Error('lease_test_timeout');await new Promise(r=>setTimeout(r,10));}
fs.mkdirSync(path.join(root,'evidence'));fs.writeFileSync(path.join(root,'evidence','report.json'),JSON.stringify({success:true,steps:[{exitCode:0}],childCompleted:true}));
`);
const calls=[],oidcRequests=[];
let accepted=initial,refreshCount=0,renewCount=0;
const call=createCoordinatorClient({url,initialToken:initial,env,fetchImpl:async(target,options)=>{
  if(String(target).startsWith('https://oidc.example/')){
    const parsed=new URL(target);
    assert.equal(parsed.searchParams.get('audience'),'arbm-continuity');
    assert.equal(parsed.searchParams.getAll('audience').length,1);
    assert.equal(options.headers.authorization,`Bearer ${credential}`);
    assert.equal(options.redirect,'error');
    refreshCount++;accepted=fresh+refreshCount;oidcRequests.push(parsed.searchParams.get('audience'));
    return response(200,{value:accepted});
  }
  const body=JSON.parse(options.body);
  calls.push({action:body.action,body:options.body,authorized:options.headers.authorization===`Bearer ${accepted}`});
  if(options.headers.authorization!==`Bearer ${accepted}`)return response(401,{error:initial+credential+fresh});
  if(body.action==='renew'){
    renewCount++;
    // The first renew expires the initially accepted token, inside a live child.
    if(renewCount===1){accepted='expired';return response(401,{error:initial+credential});}
    const pid=Number(fs.readFileSync(path.join(root,'started'),'utf8'));
    assert.doesNotThrow(()=>process.kill(pid,0),'child must stay alive through refresh');
    if(renewCount>=4)fs.writeFileSync(path.join(root,'released'),'lease alive');
  }
  return response(200,{ok:true,claimed:true});
}});
await call('heartbeat',{healthy:true});await call('claim');
const old={};for(const key of Object.keys(env).concat('ARBM_OIDC')){old[key]=process.env[key];process.env[key]=key==='ARBM_OIDC'?initial:env[key];}
try {
  const report=await executePayloadSupervised({schema:'test'},{root,runnerPath:runner,renewEveryMs:20,maxRenewMisses:2,renew:async()=>{
    if(!fs.existsSync(path.join(root,'started')))return {ok:true};
    return call('renew',{missionId:'frozen-mission'});
  }});
  assert.equal(report.childCompleted,true);assert.equal(report.runnerExitCode,0);
  assert.equal(refreshCount,1);assert.ok(renewCount>=4);
  const renews=calls.filter(c=>c.action==='renew');assert.equal(renews[0].body,renews[1].body);
  accepted='expired-again';
  await call('complete',{missionId:'frozen-mission',state:'SUCCEEDED'});
  assert.equal(refreshCount,2);
  const completes=calls.filter(c=>c.action==='complete');assert.equal(completes.length,2);assert.equal(completes[0].body,completes[1].body);
  assert.deepEqual(oidcRequests,['arbm-continuity','arbm-continuity']);
}finally {
  for(const [key,value] of Object.entries(old)){if(value===undefined)delete process.env[key];else process.env[key]=value;}
  fs.rmSync(root,{recursive:true,force:true});
}

// Exactly one refresh/retry, no retry on other errors, and no secret-bearing errors.
for(const status of [401,403,500]){
  let requests=0,refreshes=0;
  const rejected=createCoordinatorClient({url,initialToken:initial,env,fetchImpl:async(target)=>{
    if(String(target).startsWith('https://oidc.example/')){refreshes++;return response(200,{value:fresh});}
    requests++;return response(status,{error:initial+credential+fresh});
  }});
  await assert.rejects(()=>rejected('renew',{missionId:'m'}),e=>e.message===`continuity_renew_http_${status}`&&!e.message.includes(initial)&&!e.message.includes(credential)&&!e.message.includes(fresh));
  assert.equal(requests,status===401?2:1);assert.equal(refreshes,status===401?1:0);
}
const badRefresh=createCoordinatorClient({url,initialToken:initial,env,fetchImpl:async target=>{
  if(String(target).startsWith('https://oidc.example/'))throw new Error(credential+initial);
  return response(401,{error:initial});
}});
await assert.rejects(()=>badRefresh('complete'),/^Error: continuity_oidc_request_failed$/);
const noInitial=createCoordinatorClient({url,env,fetchImpl:async target=>String(target).startsWith('https://oidc.example/')?response(200,{value:fresh}):response(200,{ok:true})});
assert.equal((await noInitial('heartbeat')).ok,true);
console.log(JSON.stringify({OIDC_REFRESH_ON_401_TEST:'PASS',LEASE_LONG_RUN_TEST:'PASS',NO_TOKEN_EXPOSURE:'PASS',renewals:renewCount,refreshes:refreshCount}));
