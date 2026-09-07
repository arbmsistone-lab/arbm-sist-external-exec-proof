import fs from 'node:fs';
import path from 'node:path';
import { validatePayload } from './universal-remote-runner.mjs';
import { executePayloadSupervised } from './continuity-execution-supervisor.mjs';

const URL=process.env.ARBM_CONTINUITY_URL||'https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-continuity-coordinator-v1';
const TOKEN=String(process.env.ARBM_OIDC||'').trim();
const ROOT=process.env.ARBM_RUN_ROOT||path.join(process.cwd(),'.arbm-run');
if(!TOKEN)throw new Error('arbm_oidc_required');

async function call(action,payload={}){
  const res=await fetch(URL,{method:'POST',headers:{authorization:`Bearer ${TOKEN}`,'content-type':'application/json'},body:JSON.stringify({action,...payload}),signal:AbortSignal.timeout(15000)});
  const text=await res.text();let body;try{body=JSON.parse(text);}catch{body={raw:text};}
  if(!res.ok)throw new Error(`continuity_${action}_http_${res.status}:${body?.error||text}`);
  return body;
}
function output(k,v){if(process.env.GITHUB_OUTPUT)fs.appendFileSync(process.env.GITHUB_OUTPUT,`${k}=${String(v).replace(/[\r\n]/g,' ')}\n`);}
function errorText(error){return String(error?.code||error?.message||error).slice(0,1800);}

let leased=null;
try{
  await call('heartbeat',{healthy:true,zeroSpendVerified:true,capabilities:['git','tests','build','cloud'],detail:{source:'github-actions-oidc-runner',mode:'autonomous-continuity-worker'}});
  const claim=await call('claim');
  if(!claim.claimed){output('claimed','false');console.log(JSON.stringify({ok:true,claimed:false,state:'IDLE'}));process.exit(0);}
  leased=claim.mission;
  if(leased?.mission_kind!=='universal-remote-v1')throw new Error('unsupported_claimed_mission_kind');
  const payload=validatePayload(leased.payload||{});
  if(payload.source.repo!==leased.source_repo||payload.source.ref.toLowerCase()!==String(leased.source_sha||'').toLowerCase())throw new Error('claimed_source_binding_mismatch');
  const report=await executePayloadSupervised(payload,{root:ROOT,renew:()=>call('renew',{missionId:leased.mission_id}),renewEveryMs:60000,maxRenewMisses:2});
  fs.mkdirSync(path.join(ROOT,'evidence'),{recursive:true});
  fs.writeFileSync(path.join(ROOT,'evidence','continuity-claim.json'),JSON.stringify({missionId:leased.mission_id,leaseUntil:leased.lease_until,provider:'github-public-standard',supervisedLease:true},null,2)+'\n');
  const state=report.success?'SUCCEEDED':'FAILED_FINAL';
  const done=await call('complete',{missionId:leased.mission_id,state,error:report.success?null:'mission_result_failed'});
  if(done.ok!==true)throw new Error('continuity_complete_rejected');
  output('claimed','true');output('mission_id',leased.mission_id);output('mission_state',state);
  console.log(JSON.stringify({ok:report.success,claimed:true,missionId:leased.mission_id,state,steps:report.steps.length,supervisedLease:true}));
  process.exitCode=report.success?0:2;
}catch(error){
  const message=errorText(error);
  if(leased?.mission_id){try{await call('complete',{missionId:leased.mission_id,state:'FAILED_FINAL',error:message});}catch{}}
  output('claimed',Boolean(leased));output('mission_id',leased?.mission_id||'');output('mission_state','FAILED_FINAL');
  console.error(JSON.stringify({ok:false,claimed:Boolean(leased),missionId:leased?.mission_id||null,error:message}));
  process.exitCode=1;
}
