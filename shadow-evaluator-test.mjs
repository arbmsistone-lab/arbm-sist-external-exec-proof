import assert from 'node:assert/strict';
import { TASKS, assessRun, summarize } from './shadow-evaluator.mjs';

const byId = Object.fromEntries(TASKS.map((task) => [task.id, task]));

const okCases = {
  'add-bug': 'function add(a,b){return a+b;}',
  factorial: 'function factorial(n){if(n<=1)return 1;return n*factorial(n-1);}',
  dedupe: '[...new Set(a)]',
  promise: 'async function f(){return await Promise.resolve(7);}',
};

for (const [id, stdout] of Object.entries(okCases)) {
  const row = assessRun({status:0,error:null,stdout,stderr:'',validate:byId[id].validate,latencyMs:1});
  assert.equal(row.pass, true, id);
  assert.equal(row.failureClass, 'ok', id);
}

const runtimeFail = assessRun({status:1,error:null,stdout:'',stderr:'bad arg',validate:()=>true,latencyMs:1});
assert.equal(runtimeFail.pass, false);
assert.equal(runtimeFail.failureClass, 'runtime_error');
assert.equal(runtimeFail.stderrPreview, 'bad arg');

const semanticFail = assessRun({status:0,error:null,stdout:'function add(a,b){return a-b;}',stderr:'',validate:byId['add-bug'].validate,latencyMs:1});
assert.equal(semanticFail.failureClass, 'semantic_miss');
assert.equal(summarize('x','y',[semanticFail]).evaluatorIntegrity, true);

console.log(JSON.stringify({suite:'SHADOW-EVALUATOR-V4',pass:10,total:10,score:100}));
