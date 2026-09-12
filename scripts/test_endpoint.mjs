import fs from 'node:fs';
import vm from 'node:vm';
import { stripTypeScriptTypes } from 'node:module';
import assert from 'node:assert/strict';
const path=process.argv[2] || 'endpoint/index.ts';
let source=fs.readFileSync(path,'utf8').replace(/^import .*;\r?\n/gm,'');
source=stripTypeScriptTypes(source);
const context={console,URL,Response,Request,TextEncoder,AbortSignal,Date,Map,JSON,Number,String,Math,Set,
  createRemoteJWKSet:()=>null,jwtVerify:async()=>({payload:{repository:'arbmsistone-lab/arbm-sist-external-exec-proof',ref:'refs/heads/codex/osworld-close-test',event_name:'push',run_id:'offline',sha:'test'}}),
  Deno:{env:{get:()=>undefined},serve:f=>{context.handler=f;}}};
vm.createContext(context);vm.runInContext(source,context);
const run=s=>vm.runInContext(s,context);
assert.notEqual(run('validate("pyautogui.click(380,238),[object Object]")'),'','historical malformed array must be rejected');
assert.notEqual(run('validate("pyautogui.click(1,2),Wait for email")'),'');
assert.notEqual(run('validate("pyautogui.click(eval(1))")'),'');
assert.equal(run('validate("pyautogui.write(\'hello; world\')\\npyautogui.press(\'enter\')")'),'');
for(const action of ['EXEC','execute','plan','click','type']) {
  context.sample={action,command:"pyautogui.press('enter')"};
  assert.equal(run('canonicalAction(sample).action'),'exec');
}
assert.equal(run('canonicalAction({action:"PLAN",plan:"next"}).action'),'wait');
assert.throws(()=>run('canonicalAction({action:"exec",command:["pyautogui.click(1,2)",{}]})'));
console.log('ENDPOINT_CONTRACT_PASS');
// Exercise real handler and routing with deterministic FREE/HTTP fixtures.
const attempts=[];
context.Deno.env.get=k=>['GROQ_API_KEY','MISTRAL_API_KEY'].includes(k)?'offline-test':k.startsWith('ARBM_MISTRAL_')?'1':undefined;
const freeHeaders={'x-ratelimit-limit-requests':'1000','x-ratelimit-limit-tokens':'8000'};
const good={choices:[{message:{content:JSON.stringify({action:'EXEC',command:"pyautogui.press('enter')"})}}]};
for(const failure of [413,422,429,500,503]){
 run('COOLDOWN.clear()');let count=0;
 context.fetch=async(url,options)=>{
  attempts.push({url,body:JSON.parse(options.body)});count++;
  return new Response(JSON.stringify(count<=2?{error:{message:'offline quota fixture'}}:good),{status:count<=2?failure:200,headers:freeHeaders});
 };
 const req=new Request('https://offline.test',{method:'POST',headers:{authorization:'Bearer offline'},body:JSON.stringify({instruction:'press enter',observation:'OK button',screenshot_data_url:'data:image/png;base64,AA=='})});
 const response=await context.handler(req);const data=await response.json();
 assert.equal(response.status,200,JSON.stringify(data));
 assert.equal(data.provider,'mistral-free');assert.equal(data.paid_fallback_used,false);assert.equal(data.mandatory_cost_usd,0);
 assert.equal(data.provider_attempts.length,3);
 assert.equal(data.action.action,'exec');
 assert.equal(data.provider_attempts[2].zero_spend_confirmed,true);
}
run('COOLDOWN.clear()');
let calls=0;context.fetch=async()=>{calls++;return new Response(JSON.stringify(good),{status:200,headers:freeHeaders});};
let response=await context.handler(new Request('https://offline.test',{method:'POST',headers:{authorization:'Bearer offline'},body:JSON.stringify({instruction:'x',expected_build:'wrong',screenshot_data_url:'x'})}));
assert.equal(response.status,409);assert.equal(calls,0);
response=await context.handler(new Request('https://offline.test',{method:'POST',headers:{authorization:'Bearer offline'},body:JSON.stringify({instruction:'x',screenshot_data_url:'x'.repeat(500000)})}));
assert.equal(response.status,413);assert.equal(calls,0);
run('COOLDOWN.clear()');
context.fetch=async()=>new Response(JSON.stringify({error:{message:'quota'}}),{status:429,headers:freeHeaders});
response=await context.handler(new Request('https://offline.test',{method:'POST',headers:{authorization:'Bearer offline'},body:JSON.stringify({instruction:'x',screenshot_data_url:'x'})}));
assert.equal(response.status,503);assert.equal((await response.json()).status,'NO_ZERO_SPEND_MULTIMODAL_CAPACITY');
console.log('ENDPOINT_FAILOVER_PAYLOAD_AUTH_PASS');

assert.equal(run('textField({fact:"visible"})'),'{"fact":"visible"}');
for(const a of attempts.filter(x=>x.url.includes('groq'))){assert.equal(a.body.reasoning_effort,'none');assert.equal(a.body.max_completion_tokens,600);}
console.log('GROQ_OUTPUT_BUDGET_AND_MEMORY_PASS');
