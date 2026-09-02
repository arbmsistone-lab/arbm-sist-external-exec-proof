import {spawnSync} from 'node:child_process';
import crypto from 'node:crypto';
const cli=process.env.LLAMA_CLI,model=process.env.MODEL_PATH;
if(!cli||!model) throw new Error('runtime_required');
const tasks=[
 ['add-bug','Fix function add(a,b){return a-b}. Return only corrected JS.','returna+b'],
 ['factorial','Write JS function factorial(n) recursively. Return only code.','factorial(n-1)'],
 ['dedupe','Write JS expression returning unique values from array a. Return only expression.','newSet'],
 ['promise','Write JS that awaits Promise.resolve(7) inside async function f. Return only code.','awaitPromise.resolve(7)']
];
const rows=[];for(const [id,prompt,expect] of tasks){const t=Date.now();const r=spawnSync(cli,['-m',model,'-p',prompt,'-n','160','--temp','0','--no-display-prompt'],{encoding:'utf8',timeout:120000});const out=String(r.stdout||'');const canonical=out.replace(/\s+/g,'');rows.push({id,exitCode:r.status,latencyMs:Date.now()-t,pass:r.status===0&&canonical.includes(expect),outputSha256:crypto.createHash('sha256').update(out).digest('hex')});}
const result={schema:'arbm-shadow-lab-v2',model:'Qwen2.5-Coder-1.5B-Instruct-GGUF-Q4_K_M',runtimeCommit:'159b741427337a2e9a58b08121001545d66b5825',evaluator:'whitespace-canonical-v1',rows,pass:rows.filter(x=>x.pass).length,total:rows.length};
console.log(JSON.stringify(result));process.exit(result.pass===result.total?0:1);
