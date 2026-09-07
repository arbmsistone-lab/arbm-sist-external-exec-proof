import assert from 'node:assert/strict';
import http from 'node:http';
import {spawn} from 'node:child_process';
const seen=[];
const server=http.createServer((req,res)=>{
  let raw='';req.setEncoding('utf8');req.on('data',c=>raw+=c);req.on('end',()=>{
    const body=JSON.parse(raw||'{}');seen.push({authorization:req.headers.authorization,body});
    res.setHeader('content-type','application/json');
    res.end(JSON.stringify(body.action==='claim'?{ok:true,claimed:false}:{ok:true}));
  });
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const {port}=server.address();
const child=spawn(process.execPath,['scripts/sovereign-continuity-worker.mjs'],{
  cwd:process.cwd(),
  env:{...process.env,ARBM_CONTINUITY_URL:`http://127.0.0.1:${port}`,ARBM_OIDC:'test-oidc',GITLAB_CI:'true',ARBM_PROVIDER_ID:'gitlab-free-private',ARBM_EXTRA_CAPABILITIES:'gitlab-runner'}
});
let stdout='',stderr='';child.stdout.on('data',x=>stdout+=x);child.stderr.on('data',x=>stderr+=x);
const code=await new Promise(resolve=>child.on('close',resolve));
await new Promise(resolve=>server.close(resolve));
assert.equal(code,0,stderr);
assert.equal(seen.length,2);
const hb=seen.find(x=>x.body.action==='heartbeat');
assert.equal(hb.authorization,'Bearer test-oidc');
assert.ok(hb.body.capabilities.includes('gitlab-runner'));
assert.equal(hb.body.detail.providerLabel,'gitlab-free-private');
assert.equal(hb.body.detail.source,'oidc-continuity-worker');
assert.match(stdout,/"provider":"gitlab-free-private"/);
console.log('SOVEREIGN_CONTINUITY_MULTIPROVIDER_TEST_PASS');
