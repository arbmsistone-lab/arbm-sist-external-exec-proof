import http from 'node:http';
import { spawn } from 'node:child_process';
import { setTimeout as sleep } from 'node:timers/promises';

const port=Number(process.env.PORT||8000);
const vendor=String(process.env.ARBM_CLOUD_VENDOR||'').trim().toLowerCase();
let child=null,lastExit=null,stopping=false,restarts=0;

function startAgent(){
  child=spawn(process.execPath,['/opt/arbm/scripts/persistent-continuity-agent.mjs'],{
    stdio:'inherit',env:process.env
  });
  child.once('exit',(code,signal)=>{
    lastExit={code,signal,at:new Date().toISOString()};child=null;
    if(!stopping){restarts++;void restartLoop();}
  });
}
async function restartLoop(){await sleep(Math.min(5000*restarts,30000));if(!stopping&&!child)startAgent();}
const server=http.createServer((req,res)=>{
  if(req.url!=='/health'&&req.url!=='/'){res.writeHead(404);res.end('not found');return;}
  const body=JSON.stringify({ok:!!child,vendor,pid:child?.pid||null,restarts,lastExit});
  res.writeHead(child?200:503,{'content-type':'application/json','cache-control':'no-store'});res.end(body);
});
server.listen(port,'0.0.0.0',()=>{console.log(JSON.stringify({event:'health_server_ready',port,vendor}));startAgent();});
async function shutdown(signal){stopping=true;console.log(JSON.stringify({event:'shutdown',signal}));if(child&&!child.killed)child.kill('SIGTERM');server.close(()=>process.exit(0));setTimeout(()=>process.exit(1),8000).unref();}
process.on('SIGTERM',()=>void shutdown('SIGTERM'));process.on('SIGINT',()=>void shutdown('SIGINT'));
