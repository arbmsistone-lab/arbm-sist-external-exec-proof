import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {stripTypeScriptTypes} from "node:module";
import vm from "node:vm";
const code=stripTypeScriptTypes(readFileSync("supabase/functions/arbm-terminal-agent-v7/index.ts","utf8").replace(/^import .*;\r?\n/gm,""));
const valid={action:"exec",command:"pwd",summary:"Inspect essential-context"};
function shared(){return {providers:{},acquires:0,completes:0};}
function harness(faults={},state=shared()){
 let handler;const calls=[];const env={MISTRAL_API_KEY:"secret-mistral-test",GROQ_API_KEY:"secret-groq-test",GEMINI_API_KEY:"secret-google-test",LIGHTNING_API_KEY:"secret-lightning-test",ARBM_MISTRAL_ZERO_SPEND_CONFIRMED:"1",ARBM_MISTRAL_LIVE_PROVEN:"1",ARBM_LIGHTNING_ZERO_SPEND_CONFIRMED:"1",SUPABASE_URL:"https://control.test",SUPABASE_SERVICE_ROLE_KEY:"secret-service-test"};
 const context=vm.createContext({URL,Request,Response,Headers,AbortSignal,Date,TextEncoder,console,
 Deno:{env:{get:k=>env[k]},serve:f=>{handler=f;}},createRemoteJWKSet:()=>({}),jwtVerify:async()=>({payload:{repository:"arbmsistone-lab/arbm-sist-external-exec-proof",ref:"refs/heads/codex/free-capacity-v3-20260908",event_name:"push"}}),
 fetch:async(url,options)=>{
  const body=JSON.parse(options.body);
  if(String(url).includes("/rest/v1/rpc/")){
    if(faults.control)throw Error("control unavailable");
    const row=state.providers[body.p_provider] ||= {busy:false,cooling:false};
    if(String(url).endsWith("arbm_mesh_acquire")){
      state.acquires++;if(row.busy||row.cooling)return Response.json({allowed:false,reason:row.cooling?"cooling_down":"in_flight"});row.busy=true;return Response.json({allowed:true,lease_id:"unique-lease"});
    }
    state.completes++;row.busy=false;row.cooling=body.p_retry_seconds>0;return Response.json({accepted:true});
  }
  const provider=String(url).includes("mistral")?"mistral":String(url).includes("groq")?"groq":String(url).includes("googleapis")?"google":"lightning";
  calls.push({provider,body});const fault=faults[provider];
  if(fault=== "transport")throw Error("transport");
  if(fault)return Response.json({error:{message:"provider unavailable"}},{status:fault,headers:{"retry-after":"120"}});
  return Response.json(provider==="google"?{candidates:[{content:{parts:[{text:JSON.stringify(valid)}]}}],usageMetadata:{totalTokenCount:100}}:{choices:[{message:{content:JSON.stringify(valid)}}],usage:{total_tokens:100}},{headers:{"x-ratelimit-limit-requests":"1000","x-ratelimit-limit-tokens":"8000"}});
 }});
 vm.runInContext(code,context);
 return {calls,state,context,run:body=>handler(new Request("https://test",{method:"POST",headers:{authorization:"Bearer test"},body:JSON.stringify({instruction:"essential-context safe directory inspection",...body})}))};
}
for(const missing of ["lightning","groq","google","mistral"]){
 test(`N-1 ${missing}: another FREE provider preserves context`,async()=>{
   // Inject exactly the selected provider failure; avoid coupling health state across providers.
   const h=harness({[missing]:503});
   // On missing provider, shared mock health is per provider in real SQL; allow unrelated provider.
   assert.equal((await h.run({provider_hint:missing})).status,503);
   assert.equal(h.calls[0].provider,missing);
   const response=await h.run({step:missing==="groq"?3:1});const data=await response.json();
   {
    assert.equal(response.status,200);assert.notEqual(data.provider,{lightning:"lightning-ai-free",groq:"groqcloud-free",google:"google-gemini",mistral:"mistral-free"}[missing]);
    assert.equal(data.paid_fallback_used,false);assert.equal(data.mandatory_cost_usd,0);
   }
   assert.ok(h.calls.length<=4);assert.ok(h.calls.every(c=>JSON.stringify(c.body).includes("essential-context")));
 });
}
test("two isolates sharing one lease do not stampede Mistral",async()=>{
 const state=shared();const a=harness({},state),b=harness({},state);
 const result=await Promise.all([a.run({provider_hint:"mistral"}),b.run({provider_hint:"mistral"})]);
 assert.equal(a.calls.length+b.calls.length,1);assert.deepEqual(result.map(r=>r.status).sort(),[200,503]);
});
test("429 is visible to another isolate and no model/key rotation occurs",async()=>{
 const state=shared();const a=harness({mistral:429},state),b=harness({},state);
 assert.equal((await a.run({provider_hint:"mistral"})).status,503);
 assert.equal((await b.run({provider_hint:"mistral"})).status,503);assert.equal(a.calls.length,1);assert.equal(b.calls.length,0);
});
test("shared coordinator outage fails closed without provider calls",async()=>{
 const h=harness({control:true});assert.equal((await h.run({provider_hint:"mistral"})).status,503);assert.equal(h.calls.length,0);
});
test("secret redaction covers all provider/service keys and bearer headers",()=>{
 const h=harness();const out=vm.runInContext('scrub("secret-mistral-test secret-groq-test secret-google-test secret-lightning-test secret-service-test Bearer random-private-value")',h.context);
 assert.ok(!out.includes("secret-"));assert.ok(!out.includes("random-private-value"));
});
