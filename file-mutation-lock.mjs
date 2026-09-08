import fs from 'node:fs';
const sleepMs=ms=>Atomics.wait(new Int32Array(new SharedArrayBuffer(4)),0,0,ms);
export function withFileLock(lockPath,fn,{attempts=200,delayMs=10,staleMs=600000}={}){
  let held=false;
  for(let i=0;i<attempts&&!held;i++){
    try{fs.mkdirSync(lockPath);held=true;}
    catch(e){
      if(e?.code!=='EEXIST') throw e;
      try{const age=Date.now()-fs.statSync(lockPath).mtimeMs;if(age>staleMs){fs.rmSync(lockPath,{recursive:true,force:true});continue;}}catch{}
      sleepMs(delayMs);
    }
  }
  if(!held) throw new Error('FILE_MUTATION_LOCK_TIMEOUT:'+lockPath);
  try{return fn();}finally{fs.rmSync(lockPath,{recursive:true,force:true});}
}
