import crypto from 'node:crypto';
const input={task:'remote-code-proof',values:[2,3,5,7,11,13]};
const result=input.values.reduce((a,b)=>a+b,0);
if(result!==41) throw new Error('deterministic_mission_failed');
const evidence={runner:process.env.RUNNER_NAME||'unknown',os:process.platform,node:process.version,result,inputSha256:crypto.createHash('sha256').update(JSON.stringify(input)).digest('hex')};
evidence.outputSha256=crypto.createHash('sha256').update(JSON.stringify(evidence)).digest('hex');
console.log(JSON.stringify(evidence));
