import {spawnSync} from 'node:child_process';
import crypto from 'node:crypto';
const cli=process.env.LLAMA_CLI,model=process.env.MODEL_PATH,label=process.env.MODEL_LABEL||'unknown';
if(!cli||!model) throw new Error('runtime_required');
const tasks=[
 ['add-bug','Fix function add(a,b){return a-b}. Return only corrected JS.',/\breturn\s+a\s*\+\s*b\b/],
 ['factorial','Write JS function factorial(n) recursively. Return only code.',/factorial\s*\(\s*n\s*-\s*1\s*\)/],
 ['dedupe','Write JS expression returning unique values from array a. Return only expression.',/new\s+Set\s*\(/],
 ['promise','Write JS that awaits Promise.resolve(7) inside async function f. Return only code.',/await\s+Promise\.resolve\s*\(\s*7\s*\)/]
];
const args=['-n','160','--temp','0','--no-display-prompt','--no-show-timings','--simple-io','--no-conversation','--log-colors','off','--no-log-prefix','--no-log-timestamps'];
const rows=[];for(const [id,prompt,expect] of tasks){const t=Date.now();const r=spawnSync(cli,['-m',model,'-p',prompt,...args],{encoding:'utf8',timeout:180000,maxBuffer:256*1024});const out=String(r.stdout||'').trim(),processError=r.error?.code||null,outputChars=out.length,integrity=r.status===0&&!processError&&outputChars>0&&outputChars<=8192;rows.push({id,exitCode:r.status,processError,latencyMs:Date.now()-t,outputChars,pass:integrity&&expect.test(out),outputDigest:'sha256:'+crypto.createHash('sha256').update(out).digest('hex')});}
const result={schema:'arbm-shadow-lab-v3',model:label,runtimeCommit:'159b741427337a2e9a58b08121001545d66b5825',rows,pass:rows.filter(x=>x.pass).length,total:rows.length,evaluatorIntegrity:rows.every(x=>x.exitCode===0&&!x.processError&&x.outputChars>0&&x.outputChars<=8192)};
console.log(JSON.stringify(result));process.exit(result.pass===result.total&&result.evaluatorIntegrity?0:1);
