import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { stripTypeScriptTypes } from "node:module";
import vm from "node:vm";

const source = readFileSync("supabase/functions/arbm-terminal-agent-v7/index.ts", "utf8").replace(/^import .*;\r?\n/gm, "");
const code = stripTypeScriptTypes(source);
const action = {action:"exec",command:"pwd",summary:"Inspect directory"};
function harness(env = {}, responses = []) {
  let handler;
  const calls = [];
  const vars = {MISTRAL_API_KEY:"test-secret-never-log", ARBM_MISTRAL_ZERO_SPEND_CONFIRMED:"1", ARBM_MISTRAL_LIVE_PROVEN:"1", ...env};
  const context = vm.createContext({URL,Response,Request,Headers,AbortSignal,Date,console,
    Deno:{env:{get:key=>vars[key]},serve:fn=>{handler=fn;}},
    createRemoteJWKSet:()=>({}),
    jwtVerify:async()=>({payload:{repository:"arbmsistone-lab/arbm-sist-external-exec-proof",ref:"refs/heads/codex/free-capacity-v3-20260908",event_name:"push"}}),
    fetch:async(url,options)=>{
      calls.push({url:String(url),body:JSON.parse(options.body)});
      const response = responses.shift();
      if(response instanceof Error) throw response;
      return response || new Response(JSON.stringify({choices:[{message:{content:JSON.stringify(action)}}],usage:{total_tokens:146}}),{status:200,headers:{"x-ratelimit-remaining":"9","x-ratelimit-limit-tokens-minute":"5000","set-cookie":"private","authorization":"private"}});
    }});
  vm.runInContext(code,context);
  return {calls,context,call:(hint="")=>vm.runInContext(`callMistral("test", ${JSON.stringify(hint)})`,context),
    request:body=>handler(new Request("https://test.local",{method:"POST",headers:{authorization:"Bearer test"},body:JSON.stringify({instruction:"Inspect the directory safely",...body})}))};
}
test("live gate and zero-spend gate block network; explicit diagnostic can prove live",async()=>{
  for(const env of [{MISTRAL_API_KEY:""},{ARBM_MISTRAL_ZERO_SPEND_CONFIRMED:"0"},{ARBM_MISTRAL_LIVE_PROVEN:"0"},{ZERO_SPEND_MODE:"SOFT"}]){
    const h=harness(env); assert.equal((await h.call()).result,null); assert.equal(h.calls.length,0);
  }
  const h=harness({ARBM_MISTRAL_LIVE_PROVEN:"0"}); assert.equal((await h.call("ministral-3b-latest")).result.provider,"mistral-free");
  const invalid=harness({ARBM_MISTRAL_LIVE_PROVEN:"0"}); await invalid.call("paid-model"); assert.equal(invalid.calls.length,0);
});
test("success carries only safe rate headers and real usage",async()=>{
  const h=harness();const result=await h.call();const a=result.attempts[0];
  assert.equal(a.status,200);assert.equal(a.parsed,true);assert.equal(a.usage.total_tokens,146);
  assert.equal(a.rate_limit_headers["x-ratelimit-remaining"],"9");
  assert.equal(a.rate_limit_headers.authorization,undefined);assert.equal(a.rate_limit_headers["set-cookie"],undefined);
  assert.equal(a.mandatory_cost_usd,0);assert.equal(a.paid_fallback_used,false);
});
test("429 stops model rotation and puts entire provider into cooldown",async()=>{
  const h=harness({},[new Response("{}",{status:429,headers:{"retry-after":"120"}})]);
  assert.equal((await h.call()).attempts[0].status,429);
  assert.equal((await h.call()).attempts[0].status,"cooldown");assert.equal(h.calls.length,1);
});
test("HTTP date Retry-After is respected",()=>{
  const h=harness();assert.equal(vm.runInContext('mistralRetryMs("Wed, 09 Sep 2026 12:02:00 GMT", Date.parse("Wed, 09 Sep 2026 12:00:00 GMT"))',h.context),120000);
});
test("auth, overload, transport and malformed response never promote or rotate",async()=>{
  for(const response of [new Response("{}",{status:401}),new Response("{}",{status:403}),new Response("{}",{status:503}),new Error("network"),new Response(JSON.stringify({choices:[{message:{content:"{}"}}]}),{status:200})]){
    const h=harness({},[response]);assert.equal((await h.call()).result,null);assert.equal(h.calls.length,1);
  }
});
test("only model-specific unavailability tries the next allowed model",async()=>{
  const h=harness({},[new Response(JSON.stringify({message:"model not found"}),{status:404})]);
  const result=await h.call(); assert.equal(result.result.model,"ministral-8b-latest");
  assert.deepEqual(h.calls.map(c=>c.body.model),["ministral-3b-latest","ministral-8b-latest"]);
  const no=harness({},[new Response(JSON.stringify({message:"invalid request"}),{status:400})]);
  assert.equal((await no.call()).result,null);assert.equal(no.calls.length,1);
});
test("normal mesh reaches Mistral without provider or model hint",async()=>{
  const h=harness();const response=await h.request({});const data=await response.json();
  assert.equal(response.status,200);assert.equal(data.provider,"mistral-free");
  assert.equal(data.status,"PASS");assert.equal(data.paid_fallback_used,false);
  assert.equal(h.calls[0].url,"https://api.mistral.ai/v1/chat/completions");
});
test("forced existing provider stays isolated from Mistral",async()=>{
  const h=harness(); const response=await h.request({provider_hint:"google"});
  assert.equal(response.status,503);assert.equal(h.calls.length,0);
});
test("Mistral unavailable preserves existing Lightning fallback",async()=>{
  const h=harness({MISTRAL_API_KEY:"",LIGHTNING_API_KEY:"test",ARBM_LIGHTNING_ZERO_SPEND_CONFIRMED:"1"});
  const response=await h.request({});const data=await response.json();assert.equal(data.provider,"lightning-ai-free");
});
