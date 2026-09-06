import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {validatePayload,executePayload} from './universal-remote-runner.mjs';

const sha='a'.repeat(40),payload={schema:'arbm-universal-remote-mission-v1',requestId:'arbm-1234567890abcdef',source:{repo:'example/demo',ref:sha,visibility:'public'},mission:{objective:'validate repo',requiredCapabilities:['git','tests'],commands:['npm ci','npm test'],artifacts:['test-results.json'],timeoutMinutes:5,evidenceRequired:true}};
assert.equal(validatePayload(payload).source.ref,sha);
assert.throws(()=>validatePayload({...payload,source:{...payload.source,visibility:'private'}}),/public_source_required/);
assert.throws(()=>validatePayload({...payload,mission:{...payload.mission,commands:['sudo bash']}}),/blocked_command/);
assert.throws(()=>validatePayload({...payload,mission:{...payload.mission,commands:['echo a\necho b']}}),/blocked_command/);
const root=fs.mkdtempSync(path.join(os.tmpdir(),'arbm-universal-'));
const runner=(cmd,args,opts={})=>{
  if(cmd==='git'&&args[0]==='rev-parse')return {status:0,stdout:sha+'\n',stderr:''};
  if(cmd==='bash'){if(args[1]==='npm test')fs.writeFileSync(path.join(opts.cwd,'test-results.json'),'PASS\n');return {status:0,stdout:'ok\n',stderr:''};}
  return {status:0,stdout:'',stderr:''};
};
const report=executePayload(payload,{root,runner});
assert.equal(report.success,true);assert.equal(report.steps.length,2);assert.deepEqual(report.artifacts,['test-results.json']);
assert.equal(fs.existsSync(path.join(root,'evidence','report.json')),true);assert.equal(fs.existsSync(path.join(root,'evidence','report.sha256')),true);
console.log(JSON.stringify({suite:'UNIVERSAL_REMOTE_RUNNER',pass:10,total:10,state:'PASS'}));
