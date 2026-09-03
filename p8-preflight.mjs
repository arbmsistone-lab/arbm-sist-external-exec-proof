import os from 'node:os';
import {execFileSync} from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';

const pins = [
  {id:'swe-rebench-v2', repo:'https://github.com/SWE-rebench/SWE-rebench-V2.git', ref:'c71902a8cf8d2b725f63d51f199f4d3e56f68d2d', ramMB:2200, diskMB:4000},
  {id:'terminal-bench-4', repo:'https://github.com/harbor-framework/terminal-bench.git', ref:'452bf305c6daa62fc59061d22133a7cbc7c1572e', ramMB:4096, diskMB:6000},
  {id:'swe-milestone-1.0.2', repo:'https://github.com/DeepCommit-ai/SWE-Milestone.git', ref:'6d8b31168fd0e2ad57c0d1daa3df1556df014320', ramMB:8192, diskMB:8000},
  {id:'osworld-v2-2026.08.08', repo:'https://github.com/xlang-ai/OSWorld-V2.git', ref:'d578d2d4e0dc82b43e270fdaa7fa89d9708cd154', ramMB:8192, diskMB:20000},
  {id:'swefficiency', repo:'https://github.com/swefficiency/swefficiency.git', ref:'12d32a2d6800824a7d84bdb6797b5708e7b7957f', ramMB:16384, diskMB:12000}
];

function sh(cmd,args=[]){return execFileSync(cmd,args,{encoding:'utf8'}).trim();}
function diskFreeMB(){return Number(sh('df',['-Pm','.']).split(/\r?\n/).at(-1).trim().split(/\s+/)[3]);}
function verifyFetch(pin){
  const dir=fs.mkdtempSync('p8-pin-');
  try { sh('git',['-C',dir,'init','-q']); sh('git',['-C',dir,'remote','add','origin',pin.repo]); sh('git',['-C',dir,'fetch','-q','--depth=1','origin',pin.ref]); return sh('git',['-C',dir,'rev-parse','FETCH_HEAD'])===pin.ref; }
  finally { fs.rmSync(dir,{recursive:true,force:true}); }
}
const runner={
  cpu:os.cpus().length,
  ramMB:Math.round(os.totalmem()/1048576),
  freeRamMB:Math.round(os.freemem()/1048576),
  diskFreeMB:diskFreeMB(),
  docker:false,
  node:process.version,
  platform:`${process.platform}-${process.arch}`
};
try{runner.docker=/Docker version/i.test(sh('docker',['--version']));}catch{}

const rows=[];
for(const pin of pins){
  let pinVerified=false,error='';
  try{pinVerified=verifyFetch(pin);}catch(e){error=String(e?.message||e).slice(0,500);}
  const resourceFit=runner.ramMB>=pin.ramMB&&runner.diskFreeMB>=pin.diskMB&&runner.docker;
  rows.push({...pin,pinVerified,resourceFit,status:pinVerified&&resourceFit?'READY_FOR_HARNESS':'BLOCKED_PRECHECK',error});
}
const evidence={schema:'arbm-p8-official-preflight-v1',createdAt:new Date().toISOString(),runner,rows,policy:'QUALITY_FIRST_ZERO_SPEND_HARD',certification:'NOT_CERTIFIED'};
const json=JSON.stringify(evidence,null,2)+'\n';
fs.mkdirSync('p8-artifact',{recursive:true});
fs.writeFileSync('p8-artifact/preflight.json',json);
fs.writeFileSync('p8-artifact/preflight.sha256',crypto.createHash('sha256').update(json).digest('hex')+'  preflight.json\n');
console.log(json);
if(rows.some(x=>!x.pinVerified))process.exit(2);
