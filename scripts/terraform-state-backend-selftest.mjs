import crypto from 'node:crypto';
const BASE=process.env.ARBM_TF_STATE_URL||'https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terraform-state-v1';
const requestUrl=process.env.ACTIONS_ID_TOKEN_REQUEST_URL;
const requestToken=process.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN;
if(!requestUrl||!requestToken)throw new Error('github_oidc_environment_required');
const oidcUrl=new URL(requestUrl);oidcUrl.searchParams.set('audience','arbm-terraform-state');
const oidcRes=await fetch(oidcUrl,{headers:{authorization:`Bearer ${requestToken}`},signal:AbortSignal.timeout(15000)});
if(!oidcRes.ok)throw new Error(`oidc_http_${oidcRes.status}`);
const oidc=String((await oidcRes.json()).value||'');if(!oidc)throw new Error('oidc_token_missing');
const oidcAuth=`Basic ${Buffer.from(`github-oidc:${oidc}`).toString('base64')}`;
const issue=await fetch(`${BASE}/_session`,{method:'POST',headers:{authorization:oidcAuth},signal:AbortSignal.timeout(15000)});
if(issue.status!==200)throw new Error(`session_issue_http_${issue.status}:${await issue.text()}`);
const session=await issue.json();if(!session?.token)throw new Error('session_token_missing');
const auth=`Basic ${Buffer.from(`terraform-session:${session.token}`).toString('base64')}`;
const key=`selftest-${Date.now()}-${crypto.randomBytes(4).toString('hex')}`;
const url=`${BASE}/${key}`;
const lock1={ID:crypto.randomUUID(),Operation:'selftest',Who:'github-actions',Version:'1.16.1',Created:new Date().toISOString()};
const lock2={...lock1,ID:crypto.randomUUID()};
const state={version:4,terraform_version:'1.16.1',serial:1,lineage:crypto.randomUUID(),outputs:{},resources:[],check_results:null};async function req(method,suffix='',body=null,authorization=auth){
  const r=await fetch(url+suffix,{method,headers:{authorization,'content-type':'application/json'},body:body===null?undefined:JSON.stringify(body),signal:AbortSignal.timeout(15000)});
  return {status:r.status,text:await r.text()};
}
function expect(got,want,label){if(got!==want)throw new Error(`${label}:expected_${want}_got_${got}`);}
let locked=false;
try{
  expect((await req('GET')).status,404,'initial_get');
  expect((await req('LOCK','',lock1)).status,200,'lock');locked=true;
  expect((await req('LOCK','',lock2)).status,423,'lock_conflict');
  expect((await req('POST','',state)).status,423,'write_without_lock_id');
  expect((await req('POST',`?ID=${encodeURIComponent(lock1.ID)}`,state)).status,200,'write');
  const read=await req('GET');expect(read.status,200,'read');
  expect(JSON.parse(read.text).serial,1,'serial');
  expect((await req('UNLOCK','',lock1)).status,200,'unlock');locked=false;
  expect((await req('DELETE')).status,200,'delete');
  expect((await req('GET')).status,404,'final_get');  const revoke=await fetch(`${BASE}/_session`,{method:'DELETE',headers:{authorization:auth},signal:AbortSignal.timeout(15000)});
  expect(revoke.status,200,'session_revoke');
  expect((await req('GET','',null,auth)).status,401,'revoked_session_rejected');
  console.log(JSON.stringify({suite:'TERRAFORM_HTTP_STATE_BACKEND',state:'PASS',key,auth:'github-oidc-session'}));
} finally {
  if(locked)await req('UNLOCK','',lock1).catch(()=>{});
  await req('DELETE').catch(()=>{});
  await fetch(`${BASE}/_session`,{method:'DELETE',headers:{authorization:auth},signal:AbortSignal.timeout(15000)}).catch(()=>{});
}
