const ISS='https://token.actions.githubusercontent.com';
const AUD='arbm-sist-benchmark';
const REPO='arbmsistone-lab/arbm-sist-external-exec-proof';
const ALLOWED=new Set([
  '@cf/meta/llama-3.2-1b-instruct',
  '@cf/ibm-granite/granite-4.0-h-micro'
]);
const b64u=s=>Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/').padEnd(Math.ceil(s.length/4)*4,'=')),c=>c.charCodeAt(0));
const jsonPart=s=>JSON.parse(new TextDecoder().decode(b64u(s)));
async function verifyOidc(token){
  const p=String(token||'').split('.');
  if(p.length!==3) throw new Error('jwt_format');
  const head=jsonPart(p[0]), claims=jsonPart(p[1]);
  if(head.alg!=='RS256'||!head.kid) throw new Error('jwt_header');
  const now=Math.floor(Date.now()/1000);
  const aud=Array.isArray(claims.aud)?claims.aud:[claims.aud];
  if(claims.iss!==ISS||!aud.includes(AUD)||claims.repository!==REPO) throw new Error('jwt_claims');
  if(!String(claims.ref||'').startsWith('refs/heads/p3/cloudflare-free-dev-')) throw new Error('jwt_ref');
  if(Number(claims.exp||0)<now-15||Number(claims.nbf||0)>now+15) throw new Error('jwt_time');
  const jwks=await fetch(ISS+'/.well-known/jwks').then(r=>r.json());
  const jwk=(jwks.keys||[]).find(k=>k.kid===head.kid&&k.kty==='RSA');
  if(!jwk) throw new Error('jwk_missing');
  const key=await crypto.subtle.importKey('jwk',jwk,{name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'},false,['verify']);
  const signed=new TextEncoder().encode(p[0]+'.'+p[1]);
  const ok=await crypto.subtle.verify('RSASSA-PKCS1-v1_5',key,b64u(p[2]),signed);
  if(!ok) throw new Error('jwt_signature');
  return {run_id:String(claims.run_id||''),sha:String(claims.sha||'')};
}export default {async fetch(req,env){
  if(req.method!=='POST') return Response.json({ok:false,error:'method_not_allowed'},{status:405});
  try{
    const m=/^Bearer\s+(.+)$/i.exec(req.headers.get('authorization')||'');
    if(!m) throw new Error('auth_missing');
    const oidc=await verifyOidc(m[1]);
    const body=await req.json().catch(()=>({}));
    const model=String(body.model||'');
    if(!ALLOWED.has(model)) return Response.json({ok:false,error:'model_not_allowed'},{status:403});
    const result=await env.AI.run(model,{messages:[{role:'user',content:'Reply only ARBM_CF_CAPACITY_PASS'}],max_tokens:24});
    const text=String(result?.response||result?.choices?.[0]?.message?.content||'');
    return Response.json({
      ok:text.includes('ARBM_CF_CAPACITY_PASS'),provider:'cloudflare',model,
      mandatory_cost_usd:0,paid_fallback_used:false,github_run_id:oidc.run_id,
      marker:text.includes('ARBM_CF_CAPACITY_PASS')
    },{status:text.includes('ARBM_CF_CAPACITY_PASS')?200:422});
  }catch(e){
    const msg=String(e?.message||'error');
    const auth=/^(auth_|jwt_|jwk_)/.test(msg);
    return Response.json({ok:false,error:auth?'unauthorized':'inference_failed'},{status:auth?401:503});
  }
}};