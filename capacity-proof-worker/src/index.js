const ISS='https://token.actions.githubusercontent.com';
const AUD='arbm-sist-benchmark';
const REPO='arbmsistone-lab/arbm-sist-external-exec-proof';
const GRANITE='@cf/ibm-granite/granite-4.0-h-micro';
const ALLOWED=new Set(['@cf/meta/llama-3.2-1b-instruct',GRANITE]);
const MIN_PROMPT_TOKENS=1024;
const OUTPUT_DENOMINATOR=5;
const b64u=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/').padEnd(Math.ceil(s.length/4)*4,'=')),c=>c.charCodeAt(0));
const jsonPart=s=>JSON.parse(new TextDecoder().decode(b64u(s)));
async function verifyOidc(token){
  const p=String(token||'').split('.');
  if(p.length!==3) throw new Error('jwt_format');
  const head=jsonPart(p[0]),claims=jsonPart(p[1]);
  if(head.alg!=='RS256'||!head.kid) throw new Error('jwt_header');
  const now=Math.floor(Date.now()/1000),aud=Array.isArray(claims.aud)?claims.aud:[claims.aud];
  if(claims.iss!==ISS||!aud.includes(AUD)||claims.repository!==REPO) throw new Error('jwt_claims');
  if(!String(claims.ref||'').startsWith('refs/heads/p3/cloudflare-free-dev-')) throw new Error('jwt_ref');
  if(Number(claims.exp||0)<now-15||Number(claims.nbf||0)>now+15) throw new Error('jwt_time');
  const jwks=await fetch(ISS+'/.well-known/jwks').then(r=>r.json());
  const jwk=(jwks.keys||[]).find(k=>k.kid===head.kid&&k.kty==='RSA');
  if(!jwk) throw new Error('jwk_missing');
  const key=await crypto.subtle.importKey('jwk',jwk,{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['verify']);
  const ok=await crypto.subtle.verify('RSASSA-PKCS1-v1_5',key,b64u(p[2]),new TextEncoder().encode(p[0]+'.'+p[1]));
  if(!ok) throw new Error('jwt_signature');
  return {run_id:String(claims.run_id||''),sha:String(claims.sha||'')};
}
const usage=r=>({prompt_tokens:Number(r?.usage?.prompt_tokens),completion_tokens:Number(r?.usage?.completion_tokens),total_tokens:Number(r?.usage?.total_tokens)});
const validUsage=u=>Number.isInteger(u.prompt_tokens)&&u.prompt_tokens>0&&Number.isInteger(u.completion_tokens)&&u.completion_tokens>=0&&Number.isInteger(u.total_tokens)&&u.total_tokens>=u.prompt_tokens;async function capacityLane(env,body,oidc){
  const prompt=String(body.prompt||'').trim();
  const requested=Math.max(1,Math.min(512,Number(body.max_output_tokens||0)|0));
  if(!prompt) return Response.json({ok:false,error:'prompt_required'},{status:400});
  const pre=await env.AI.run(GRANITE,{messages:[{role:'user',content:prompt}],max_tokens:1});
  const preUsage=usage(pre);
  if(!validUsage(preUsage)) return Response.json({ok:false,error:'usage_unavailable'},{status:422});
  if(preUsage.prompt_tokens<MIN_PROMPT_TOKENS) return Response.json({ok:false,error:'prompt_too_short',prompt_tokens:preUsage.prompt_tokens},{status:422});
  const ceiling=Math.floor(preUsage.prompt_tokens/OUTPUT_DENOMINATOR);
  if(requested>ceiling) return Response.json({ok:false,error:'output_ratio_exceeded',prompt_tokens:preUsage.prompt_tokens,max_allowed_output_tokens:ceiling},{status:422});
  const main=await env.AI.run(GRANITE,{messages:[{role:'user',content:prompt}],max_tokens:requested});
  const mainUsage=usage(main),text=String(main?.response||main?.choices?.[0]?.message?.content||'');
  if(!validUsage(mainUsage)||mainUsage.prompt_tokens!==preUsage.prompt_tokens) return Response.json({ok:false,error:'usage_contract_failed'},{status:422});
  if(mainUsage.completion_tokens>requested) return Response.json({ok:false,error:'output_limit_failed'},{status:422});
  return Response.json({ok:text.trim().length>0,provider:'cloudflare',model:GRANITE,mode:'GRANITE_RATIO_20',mandatory_cost_usd:0,paid_fallback_used:false,github_run_id:oidc.run_id,preflight_usage:preUsage,main_usage:mainUsage,max_output_tokens:requested,max_allowed_output_tokens:ceiling,ratio_denominator:OUTPUT_DENOMINATOR,min_prompt_tokens:MIN_PROMPT_TOKENS,response_nonempty:text.trim().length>0},{status:text.trim().length>0?200:422});
}
export default {async fetch(req,env){
  if(req.method!=='POST') return Response.json({ok:false,error:'method_not_allowed'},{status:405});
  try{
    const m=/^Bearer\s+(.+)$/i.exec(req.headers.get('authorization')||'');
    if(!m) throw new Error('auth_missing');
    const oidc=await verifyOidc(m[1]);
    const body=await req.json().catch(()=>({}));
    if(body.mode==='capacity_lane') return capacityLane(env,body,oidc);
    const model=String(body.model||'');
    if(!ALLOWED.has(model)) return Response.json({ok:false,error:'model_not_allowed'},{status:403});    const result=await env.AI.run(model,{messages:[{role:'user',content:'Reply with a short capacity probe response.'}],max_tokens:24});
    const text=String(result?.response||result?.choices?.[0]?.message?.content||'');
    const nonempty=text.trim().length>0;
    return Response.json({ok:nonempty,provider:'cloudflare',model,mandatory_cost_usd:0,paid_fallback_used:false,github_run_id:oidc.run_id,response_nonempty:nonempty,usage:usage(result)},{status:nonempty?200:422});
  }catch(e){
    const msg=String(e?.message||'error');
    const auth=/^(auth_|jwt_|jwk_)/.test(msg);
    return Response.json({ok:false,error:auth?'unauthorized':'inference_failed'},{status:auth?401:503});
  }
}};
