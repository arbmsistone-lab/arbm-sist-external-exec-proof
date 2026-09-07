import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { executePayloadSupervised } from './continuity-execution-supervisor.mjs';

const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'arbm-lease-test-'));
const fake=path.join(tmp,'fake-runner.mjs');
fs.writeFileSync(fake,`import fs from 'node:fs';import path from 'node:path';
const root=process.env.ARBM_RUN_ROOT;await new Promise(r=>setTimeout(r,240));
const e=path.join(root,'evidence');fs.mkdirSync(e,{recursive:true});
fs.writeFileSync(path.join(e,'report.json'),JSON.stringify({success:true,steps:[{exitCode:0}]}));\n`);

let renews=0;
const root1=path.join(tmp,'ok');
const report=await executePayloadSupervised({schema:'test'},{
  root:root1,runnerPath:fake,renewEveryMs:40,maxRenewMisses:2,
  renew:async()=>{renews+=1;return {ok:true};}
});
assert.equal(report.success,true);
assert.ok(renews>=3,`expected renewals, got ${renews}`);
let rejected=false;
const started=Date.now();
try{
  await executePayloadSupervised({schema:'test'},{
    root:path.join(tmp,'reject'),runnerPath:fake,renewEveryMs:40,maxRenewMisses:2,
    renew:async()=>{throw new Error('coordinator_unreachable');}
  });
}catch(error){
  rejected=/lease_renewal_failed/.test(String(error?.message||error));
}
assert.equal(rejected,true,'renewal failure must fail closed');
assert.ok(Date.now()-started<1000,'failed lease should terminate child early');
fs.rmSync(tmp,{recursive:true,force:true});
console.log(JSON.stringify({suite:'CONTINUITY_EXECUTION_SUPERVISOR',state:'PASS',renewals:renews}));
