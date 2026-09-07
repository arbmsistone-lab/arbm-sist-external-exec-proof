import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const RUNNER=fileURLToPath(new URL('./universal-remote-runner.mjs',import.meta.url));
function trim(v,max=32768){const s=String(v||'');return s.length>max?s.slice(-max):s;}
function terminateTree(child){
  if(!child||child.exitCode!==null)return;
  try{
    if(process.platform==='win32') child.kill('SIGTERM');
    else process.kill(-child.pid,'SIGTERM');
  }catch{try{child.kill('SIGTERM');}catch{}}
}

export async function executePayloadSupervised(payload,{root,renew,renewEveryMs=60000,maxRenewMisses=2,runnerPath=RUNNER}={}){
  if(typeof renew!=='function')throw new Error('lease_renew_function_required');
  fs.mkdirSync(root,{recursive:true});
  const missionB64=Buffer.from(JSON.stringify(payload),'utf8').toString('base64url');
  const child=spawn(process.execPath,[runnerPath],{
    env:{...process.env,MISSION_B64:missionB64,ARBM_RUN_ROOT:root},
    stdio:['ignore','pipe','pipe'],
    detached:process.platform!=='win32'
  });
  let stdout='',stderr='',misses=0,renewalError=null;
  child.stdout.on('data',d=>{stdout=trim(stdout+d)});
  child.stderr.on('data',d=>{stderr=trim(stderr+d)});
  const timer=setInterval(async()=>{
    try{
      const result=await renew();
      if(result?.ok!==true)throw new Error('lease_renew_rejected');
      misses=0;
    }catch(error){
      misses+=1;
      if(misses>=maxRenewMisses){
        renewalError=error;
        terminateTree(child);
      }
    }
  },renewEveryMs);
  timer.unref?.();

  const code=await new Promise((resolve,reject)=>{
    child.once('error',reject);
    child.once('close',(exitCode)=>resolve(exitCode));
  }).finally(()=>clearInterval(timer));
  if(renewalError)throw new Error(`lease_renewal_failed:${renewalError?.message||renewalError}`);
  const reportPath=path.join(root,'evidence','report.json');
  if(!fs.existsSync(reportPath))throw new Error(`universal_runner_no_report:exit_${code}:${trim(stderr,2048)}`);
  let report;
  try{report=JSON.parse(fs.readFileSync(reportPath,'utf8'));}catch{throw new Error('universal_runner_invalid_report');}
  if(code!==0&&code!==2)throw new Error(`universal_runner_exit_${code}:${trim(stderr,2048)}`);
  return {...report,runnerExitCode:code,runnerStdout:trim(stdout,4096),runnerStderr:trim(stderr,4096)};
}
