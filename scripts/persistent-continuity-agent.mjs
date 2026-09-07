import os from 'node:os';
import path from 'node:path';
import { setTimeout as sleep } from 'node:timers/promises';
import { validatePayload } from './universal-remote-runner.mjs';
import { executePayloadSupervised } from './continuity-execution-supervisor.mjs';

const URL=process.env.ARBM_CONTINUITY_URL||'https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-continuity-coordinator-v1';
const HOST_ID=String(process.env.ARBM_HOST_ID||'oci-always-free-persistent').trim();
const TOKEN=String(process.env.ARBM_HOST_TOKEN||'').trim();
const INSTANCE_ID=String(process.env.ARBM_INSTANCE_ID||os.hostname()).trim();
const ROOT=process.env.ARBM_RUN_ROOT||'/var/lib/arbm-continuity/run';
const CAPS=['git','tests','build','cloud','persistent'];
if(TOKEN.length<40)throw new Error('persistent_host_token_required');
if(process.env.ARBM_ZERO_SPEND_VERIFIED!=='1')throw new Error('zero_spend_attestation_required');

async function call(action,payload={}){
  const res=await fetch(URL,{method:'POST',headers:{authorization:`Bearer ${TOKEN}`,'x-arbm-host-id':HOST_ID,'content-type':'application/json'},body:JSON.stringify({action,instanceId:INSTANCE_ID,...payload}),signal:AbortSignal.timeout(15000)});
  const text=await res.text();let body;try{body=JSON.parse(text);}catch{body={raw:text};}
  if(!res.ok)throw new Error(`continuity_${action}_http_${res.status}:${body?.error||text}`);
  return body;
}
function err(error){return String(error?.code||error?.message||error).slice(0,1800);}
async function heartbeat(){return call('heartbeat',{healthy:true,zeroSpendVerified:true,capabilities:CAPS,detail:{source:'persistent-host-agent',instanceId:INSTANCE_ID,mode:'resident-daemon'}});}
async function runOne(){
  await heartbeat();
  const claim=await call('claim');
  if(!claim.claimed)return false;
  const leased=claim.mission;
  try{
    if(leased?.mission_kind!=='universal-remote-v1')throw new Error('unsupported_claimed_mission_kind');
    const payload=validatePayload(leased.payload||{});
    if(payload.source.repo!==leased.source_repo||payload.source.ref.toLowerCase()!==String(leased.source_sha||'').toLowerCase())throw new Error('claimed_source_binding_mismatch');
    const report=await executePayloadSupervised(payload,{root:ROOT,renew:()=>call('renew',{missionId:leased.mission_id}),renewEveryMs:60000,maxRenewMisses:2});
    const state=report.success?'SUCCEEDED':'FAILED_FINAL';
    const done=await call('complete',{missionId:leased.mission_id,state,error:report.success?null:'mission_result_failed'});
    if(done.ok!==true)throw new Error('continuity_complete_rejected');
    console.log(JSON.stringify({event:'mission_complete',missionId:leased.mission_id,state,steps:report.steps.length}));
  }catch(error){
    const message=err(error);
    const transient=/lease_renewal_failed|fetch failed|timeout|ECONN|ENOTFOUND|EAI_AGAIN/i.test(message);
    try{
      if(transient)await call('failover',{missionId:leased.mission_id,failureClass:'persistent_host_failure',error:message});
      else await call('complete',{missionId:leased.mission_id,state:'FAILED_FINAL',error:message});
    }catch{}
    console.error(JSON.stringify({event:'mission_error',missionId:leased.mission_id,transient,error:message}));
  }
  return true;
}
let backoffMs=5000;
for(;;){
  try{
    const worked=await runOne();
    backoffMs=5000;
    await sleep(worked?1000:20000);
  }catch(error){
    console.error(JSON.stringify({event:'agent_cycle_error',error:err(error),backoffMs}));
    await sleep(backoffMs);
    backoffMs=Math.min(backoffMs*2,60000);
  }
}
