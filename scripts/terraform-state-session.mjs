import fs from 'node:fs';
const BASE=process.env.ARBM_TF_STATE_URL||'https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terraform-state-v1';
const mode=process.argv[2]||'issue';
const basic=(u,p)=>`Basic ${Buffer.from(`${u}:${p}`).toString('base64')}`;
if(mode==='issue'){
  const requestUrl=process.env.ACTIONS_ID_TOKEN_REQUEST_URL,requestToken=process.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN;
  if(!requestUrl||!requestToken||!process.env.GITHUB_ENV)throw new Error('github_oidc_environment_required');
  const u=new URL(requestUrl);u.searchParams.set('audience','arbm-terraform-state');
  const r=await fetch(u,{headers:{authorization:`Bearer ${requestToken}`},signal:AbortSignal.timeout(15000)});
  if(!r.ok)throw new Error(`oidc_http_${r.status}`);
  const jwt=String((await r.json()).value||'');if(!jwt)throw new Error('oidc_token_missing');
  const s=await fetch(`${BASE}/_session`,{method:'POST',headers:{authorization:basic('github-oidc',jwt)},signal:AbortSignal.timeout(15000)});
  if(!s.ok)throw new Error(`session_issue_http_${s.status}:${await s.text()}`);
  const body=await s.json(),token=String(body.token||'');if(!token)throw new Error('session_token_missing');
  console.log(`::add-mask::${token}`);
  fs.appendFileSync(process.env.GITHUB_ENV,`TF_HTTP_PASSWORD=${token}\nARBM_TF_STATE_SESSION_TOKEN=${token}\n`);
  console.log(JSON.stringify({event:'terraform_state_session_issued',expiresAt:body.expiresAt}));
}else if(mode==='revoke'){
  const token=String(process.env.ARBM_TF_STATE_SESSION_TOKEN||'');
  if(!token){console.log(JSON.stringify({event:'terraform_state_session_absent'}));process.exit(0);}
  const r=await fetch(`${BASE}/_session`,{method:'DELETE',headers:{authorization:basic('terraform-session',token)},signal:AbortSignal.timeout(15000)});
  if(!r.ok&&r.status!==401)throw new Error(`session_revoke_http_${r.status}:${await r.text()}`);
  console.log(JSON.stringify({event:'terraform_state_session_revoked',status:r.status}));
}else throw new Error('unsupported_mode');
