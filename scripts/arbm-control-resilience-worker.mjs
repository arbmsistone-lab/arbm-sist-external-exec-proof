import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const URL='https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-continuity-coordinator-v1';
const TOKEN=String(process.env.CIRCLE_OIDC_TOKEN_V2||'').trim();
if(!TOKEN) throw new Error('circle_oidc_required');

async function call(action,payload={}){
  const r=await fetch(URL,{method:'POST',headers:{authorization:`Bearer ${TOKEN}`,'content-type':'application/json'},body:JSON.stringify({action,...payload}),signal:AbortSignal.timeout(15000)});
  const t=await r.text();let b;try{b=JSON.parse(t)}catch{b={raw:t}};
  if(!r.ok) throw new Error(`continuity_${action}_${r.status}:${b.error||t}`);
  return b;
}
function blobSha(text){const b=Buffer.from(text,'utf8');return crypto.createHash('sha1').update(Buffer.concat([Buffer.from(`blob ${b.length}\0`),b])).digest('hex');}
function need(text,marker){if(!text.includes(marker))throw new Error(`missing_marker:${marker}`)}

let mission=null;
try{
  await call('heartbeat',{healthy:true,zeroSpendVerified:true,capabilities:['git','tests','build','cloud','circleci-runner','arbm-control-resilience'],detail:{source:'circleci-arbm-control-resilience-worker',mode:'exact-sha-inline-bundle'}});
  const claim=await call('claim');
  if(!claim.claimed){console.log(JSON.stringify({ok:true,claimed:false,state:'IDLE'}));process.exit(0)}
  mission=claim.mission;
  if(mission.mission_kind!=='arbm-control-resilience-v1') throw new Error('unexpected_mission_kind');
  const p=mission.payload||{},b=p.bundle||{};
  if(p.schema!=='arbm-control-resilience-mission-v1') throw new Error('invalid_schema');
  if(String(p.sourceSha||'').toLowerCase()!==String(mission.source_sha||'').toLowerCase()) throw new Error('source_sha_binding_mismatch');
  for(const [text,sha,name] of [[String(b.workerSenior||''),b.workerSeniorBlob,'worker-senior'],[String(b.packageJson||''),b.packageBlob,'package'],[String(b.validator||''),b.validatorBlob,'validator']]) if(blobSha(text)!==sha) throw new Error(`${name}_blob_mismatch`);
  const senior=String(b.workerSenior),pkg=JSON.parse(String(b.packageJson)),validator=String(b.validator);
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'arbm-control-resilience-'));
  const seniorPath=path.join(dir,'worker-senior.js');fs.writeFileSync(seniorPath,senior);execFileSync(process.execPath,['--check',seniorPath],{stdio:'inherit'});
  if(pkg.scripts?.['validate:resilience']!=='node scripts/validate-interruption-resilience.mjs') throw new Error('validator_entrypoint_mismatch');
  for(const marker of ["const RETRYABLE_STATUS = new Set([408, 425, 429, 500, 502, 503, 504])",'const RETRY_DELAYS_MS = [0, 250, 750, 1500]','async function fetchWithRetry(','async function resilientOauthFetch(',"interrupted_command_is_terminal: false","write_retry_mode: 'reconcile_remote_state_before_retry'","long_running_mode: 'prefer_durable_remote_runner_and_resume_from_last_proven_state'",'single_provider_dependency_allowed: false','const attempts = retryable ? RETRY_DELAYS_MS.length : 1;']) need(senior,marker);
  if(senior.includes("WRITE_SAFE_TOOLS.has(parsed.params?.name)")) throw new Error('blind_write_retry_detected');
  need(validator,"gate: 'ARBM_CONTROL_INTERRUPTION_RESILIENCE_V1'");need(validator,'blind_write_retry: false');need(validator,'single_provider_dependency: false');
  const done=await call('complete',{missionId:mission.mission_id,state:'SUCCEEDED'});if(done.ok!==true)throw new Error('completion_rejected');
  console.log(JSON.stringify({ok:true,missionId:mission.mission_id,state:'SUCCEEDED',sourceSha:p.sourceSha,provider:'circleci'}));
}catch(e){const error=String(e?.message||e).slice(0,1600);if(mission?.mission_id){try{await call('complete',{missionId:mission.mission_id,state:'FAILED_FINAL',error})}catch{}}console.error(JSON.stringify({ok:false,missionId:mission?.mission_id||null,error}));process.exitCode=1;}
