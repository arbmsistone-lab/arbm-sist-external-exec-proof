import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
const nodeTests=['p8-external-proof-attestor-test.mjs','incumbent-attestor-test.mjs','incumbent-registry-updater-test.mjs','replacement-proposal-gate-test.mjs','replacement-proposal-queue-test.mjs','replacement-certification-test.mjs','incumbent-promotion-controller-test.mjs','universal-radar-evidence-ledger-test.mjs','universal-radar-event-applier-test.mjs','universal-radar-scheduler-test.mjs','universal-radar-engine-test.mjs','universal-radar-change-intelligence-test.mjs','universal-radar-collector-test.mjs','universal-radar-policy-test.mjs','challenger-orchestrator-test.mjs','comparative-challenger-engine-test.mjs','universal-radar-strategy-brain-test.mjs','universal-radar-strategy-zero-spend-test.mjs'];
const pythonTests=['p8-swe-rebench-smoke-test.py','p8-quality-cost-endpoint-test.py'];
const results=[];
function run(kind,file){
  const cmd=kind==='node'?process.execPath:(process.platform==='win32'?'python':'python3');
  const r=spawnSync(cmd,[file],{encoding:'utf8',timeout:120000});
  results.push({kind,file,exitCode:r.status,pass:r.status===0,stdout:String(r.stdout||'').slice(-4000),stderr:String(r.stderr||'').slice(-4000)});
}
for(const f of nodeTests) run('node',f);
for(const f of pythonTests) run('python',f);
const evidence={schema:'arbm-core-failclosed-test-evidence-v1',generatedAt:new Date().toISOString(),sourceCommit:process.env.GITHUB_SHA||process.env.ARBM_SOURCE_SHA||'local',results,passed:results.filter(x=>x.pass).length,total:results.length,status:results.every(x=>x.pass)?'PASS':'FAIL'};
fs.mkdirSync('evidence/core-failclosed',{recursive:true});
fs.writeFileSync('evidence/core-failclosed/test-results.json',JSON.stringify(evidence,null,2)+'\n');
console.log(JSON.stringify({status:evidence.status,passed:evidence.passed,total:evidence.total}));
if(evidence.status!=='PASS') process.exit(1);