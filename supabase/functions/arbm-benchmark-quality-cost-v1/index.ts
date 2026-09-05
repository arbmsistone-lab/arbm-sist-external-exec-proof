import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@5.10.0";

const ISS="https://token.actions.githubusercontent.com";
const AUD="arbm-sist-benchmark";
const REPO="arbmsistone-lab/arbm-sist-external-exec-proof";
const JWKS=createRemoteJWKSet(new URL(ISS+"/.well-known/jwks"));
const OPENAI_URL="https://api.openai.com/v1/responses";
const PRIMARY="gpt-5.6-luna";
const ESCALATION="gpt-5.6-terra";

const PRICE:any={
  "gpt-5.6-luna":{input:0.20,cached:0.02,output:1.20},
  "gpt-5.6-terra":{input:2.00,cached:0.20,output:12.00},
};
const respond=(x:any,s=200)=>new Response(JSON.stringify(x),{status:s,headers:{"content-type":"application/json","cache-control":"no-store","x-content-type-options":"nosniff"}});

async function auth(req:Request){
  const m=/^Bearer\s+(.+)$/i.exec(req.headers.get("authorization")||"");
  if(!m) throw new Error("OIDC_MISSING");
  const {payload}=await jwtVerify(m[1],JWKS,{issuer:ISS,audience:AUD,algorithms:["RS256"]});
  if(payload.repository!==REPO) throw new Error("OIDC_REPOSITORY");
  const ref=String(payload.ref||"");
  if(!ref.startsWith("refs/heads/p8/")) throw new Error("OIDC_REF");
  if(!new Set(["push","workflow_dispatch"]).has(String(payload.event_name||""))) throw new Error("OIDC_EVENT");
  return {runId:String(payload.run_id||""),sha:String(payload.sha||"")};
}

function parseJson(text:string){
  let s=String(text||"").trim().replace(/^```(?:json)?\s*/i,"").replace(/\s*```$/i,"").trim();
  for(let i=0;i<4;i++){
    try{const p=JSON.parse(s); if(typeof p==="string"){s=p.trim();continue} return p}catch{}
    const a=s.indexOf("{"); const b=s.lastIndexOf("}");
    if(a>=0&&b>a){s=s.slice(a,b+1);continue}
    break;
  }
  return null;
}

function responseText(raw:any){
  if(typeof raw?.output_text==="string") return raw.output_text;
  const out=raw?.output||[]; const parts:string[]=[];
  for(const item of out) for(const c of item?.content||[]) if(typeof c?.text==="string") parts.push(c.text);
  return parts.join("");
}

function costUsd(model:string,usage:any){
  const p=PRICE[model]||PRICE[PRIMARY];
  const input=Number(usage?.input_tokens||0), output=Number(usage?.output_tokens||0);
  const cached=Number(usage?.input_tokens_details?.cached_tokens||0);
  const uncached=Math.max(0,input-cached);
  return (uncached*p.input+cached*p.cached+output*p.output)/1_000_000;
}

async function callOpenAI(model:string,prompt:string,key:string,maxOutput:number){
  const body:any={
    model,
    input:[{role:"system",content:[{type:"input_text",text:"You are a precise blind software repair agent. Use only the public material supplied. Never use hidden tests, gold patches, solution PRs, or evaluator feedback. Return JSON only."}]},{role:"user",content:[{type:"input_text",text:prompt}]}],
    reasoning:{effort:model===ESCALATION?"high":"medium"},
    text:{verbosity:"low"},
    max_output_tokens:maxOutput,
    store:false
  };
  const t=Date.now();
  try{
    const r=await fetch(OPENAI_URL,{method:"POST",headers:{"content-type":"application/json","authorization":"Bearer "+key},body:JSON.stringify(body),signal:AbortSignal.timeout(45000)});
    const raw=await r.json().catch(()=>({}));
    const text=responseText(raw); const parsed=parseJson(text); const usage=raw?.usage||{};
    return {ok:r.ok&&!!parsed,http:r.status,model,parsed,text,error:String(raw?.error?.message||"").slice(0,400),latency_ms:Date.now()-t,usage,cost:costUsd(model,usage)};
  }catch(e:any){
    return {ok:false,http:598,model,parsed:null,text:"",error:String(e?.message||e).slice(0,400),latency_ms:Date.now()-t,usage:{},cost:0};
  }
}

function cleanEdits(x:any){
  const src=Array.isArray(x?.edits)?x.edits:[];
  return src.slice(0,4).map((e:any)=>({path:String(e?.path||"").replace(/\\/g,"/").replace(/^\/+/,""),start_line:Number(e?.start_line),end_line:Number(e?.end_line),new:String(e?.new||"")})).filter((e:any)=>e.path&&Number.isInteger(e.start_line)&&Number.isInteger(e.end_line)&&e.end_line>=e.start_line&&e.new.trim());
}

function promptFor(phase:string,b:any){
  const issue=String(b?.issue||"").slice(0,10000), ctx=String(b?.tool_context||"").slice(0,36000);
  if(phase==="plan") return `Return ONLY JSON {"plan":{"queries":[...],"paths":[...]}}. Choose narrow public repository searches and likely tracked source paths.\nPUBLIC ISSUE:\n${issue}\nPUBLIC REPOSITORY INDEX:\n${String(b?.repo_index||"").slice(0,22000)}`;
  if(phase==="judge") return `Return ONLY JSON {"choice":"A"|"B"|"NONE","reason":"..."}. Choose only a candidate supported by public issue, context and public validation metadata.\nISSUE:\n${issue}\nCONTEXT:\n${ctx}\nA:\n${JSON.stringify(b?.candidate_a||{})}\nB:\n${JSON.stringify(b?.candidate_b||{})}\nVALIDATION A:\n${JSON.stringify(b?.validation_a||{}).slice(0,6000)}\nVALIDATION B:\n${JSON.stringify(b?.validation_b||{}).slice(0,6000)}`;
  const feedback=String(b?.public_validation_feedback||"").slice(0,5000);
  const rejected=JSON.stringify(b?.rejected_edits||[]).slice(0,5000);
  const ledger=JSON.stringify(b?.public_constraint_ledger||[]).slice(0,5000);
  const hints=JSON.stringify(b?.public_causal_hints||[]).slice(0,3000);
  return `Return ONLY JSON {"edits":[{"path":"...","start_line":1,"end_line":1,"new":"..."}]}. Produce the smallest complete fix against the ORIGINAL numbered public source. Preserve existing control flow and ordinary behavior unless public evidence requires change. Do not edit tests unless the issue explicitly requires it.\nPUBLIC ISSUE:\n${issue}\nPUBLIC TOOL CONTEXT:\n${ctx}\nPUBLIC VALIDATION FEEDBACK:\n${feedback}\nREJECTED PUBLIC CANDIDATE:\n${rejected}\nPUBLIC CONSTRAINT LEDGER:\n${ledger}\nPUBLIC CAUSAL HINTS:\n${hints}`;
}

Deno.serve(async(req:Request)=>{
  if(req.method!=="POST") return respond({error:"METHOD_NOT_ALLOWED"},405);
  try{
    const oidc=await auth(req); const b=await req.json().catch(()=>({}));
    const phase=String(b?.phase||"solve");
    if(!new Set(["plan","solve","judge"]).has(phase)) return respond({error:"PHASE_INVALID"},400);
    const key=String(Deno.env.get("OPENAI_API_KEY")||"").trim();
    if(!key) return respond({ok:false,status:"WAITING_PAID_CAPACITY",pipeline:"quality-cost-v1",mandatory_cost_usd:0,attempts:[]},503);
    const hard=phase==="solve"&&(String(b?.public_validation_feedback||"").trim()!==""||(Array.isArray(b?.failed_candidate_fingerprints)&&b.failed_candidate_fingerprints.length>=1));
    const model=hard?ESCALATION:PRIMARY; const prompt=promptFor(phase,b);
    const r=await callOpenAI(model,prompt,key,phase==="solve"?1800:1000);
    const attempts=[{stage:phase,model:r.model,http:r.http,latency_ms:r.latency_ms,parsed:!!r.parsed,provider_error:r.error,cost_usd:Number(r.cost.toFixed(8)),input_tokens:Number(r.usage?.input_tokens||0),output_tokens:Number(r.usage?.output_tokens||0)}];
    if(!r.ok) return respond({ok:false,status:"PAID_PROVIDER_UNAVAILABLE",pipeline:"quality-cost-v1",mandatory_cost_usd:Number(r.cost.toFixed(8)),attempts},503);
    const usage=r.usage||{}; const common={ok:true,status:"PASS",pipeline:"quality-cost-v1",model:r.model,mandatory_cost_usd:Number(r.cost.toFixed(8)),input_tokens:Number(usage?.input_tokens||0),output_tokens:Number(usage?.output_tokens||0),total_tokens:Number(usage?.total_tokens||0),attempts,github_run_id:oidc.runId,github_sha:oidc.sha};
    if(phase==="plan") return respond({...common,plan:r.parsed?.plan||r.parsed});
    if(phase==="judge"){
      const choice=String(r.parsed?.choice||"NONE").toUpperCase();
      return respond({...common,choice:new Set(["A","B"]).has(choice)?choice:"NONE",reason:String(r.parsed?.reason||"").slice(0,1000)});
    }
    const edits=cleanEdits(r.parsed); if(!edits.length) return respond({ok:false,status:"NO_VALID_EDITS",pipeline:"quality-cost-v1",mandatory_cost_usd:Number(r.cost.toFixed(8)),attempts},503);
    return respond({...common,edits});
  }catch(e:any){
    const msg=String(e?.message||e); const authFail=msg.startsWith("OIDC_")||msg.includes("JWT")||msg.includes("signature");
    return respond({error:authFail?"OIDC_UNAUTHORIZED":"INTERNAL_ERROR",detail:authFail?msg:undefined},authFail?401:500);
  }
});
