import assert from 'node:assert/strict';
import {collectCloudAttestation} from './cloud-host-attestation.mjs';

function response(body){return {ok:true,text:async()=>String(body),json:async()=>body};}
function withEnv(values,fn){const old={};for(const [k,v] of Object.entries(values)){old[k]=process.env[k];process.env[k]=v;}return Promise.resolve(fn()).finally(()=>{for(const [k,v] of Object.entries(old)){if(v===undefined)delete process.env[k];else process.env[k]=v;}});}

const back4app=await withEnv({ARBM_INSTANCE_ID:'b4a-test',ARBM_CPU_CORES:'0.25',ARBM_MEMORY_MIB:'256'},()=>collectCloudAttestation('back4app'));
assert.equal(back4app.instanceId,'b4a-test');
assert.equal(back4app.profile,'back4app-free-container');
assert.equal(back4app.profileEligible,true);

const back4appTooLarge=await withEnv({ARBM_INSTANCE_ID:'b4a-bad',ARBM_CPU_CORES:'0.5',ARBM_MEMORY_MIB:'512'},()=>collectCloudAttestation('back4app'));
assert.equal(back4appTooLarge.profileEligible,false);

const claw=await withEnv({ARBM_INSTANCE_ID:'claw-test',ARBM_CPU_CORES:'0.25',ARBM_MEMORY_MIB:'1024'},()=>collectCloudAttestation('clawcloud'));
assert.equal(claw.instanceId,'claw-test');
assert.equal(claw.profile,'clawcloud-free-container');
assert.equal(claw.profileEligible,true);

const clawTooLarge=await withEnv({ARBM_INSTANCE_ID:'claw-bad',ARBM_CPU_CORES:'0.5',ARBM_MEMORY_MIB:'2048'},()=>collectCloudAttestation('clawcloud'));
assert.equal(clawTooLarge.profileEligible,false);
const values={'/id':'123456789','/machine-type':'projects/1/machineTypes/e2-micro','/zone':'projects/1/zones/us-central1-a'};
const gcpFetch=async url=>response(values[new URL(url).pathname.replace('/computeMetadata/v1/instance','')]);
const gcp=await collectCloudAttestation('gcp',{fetchImpl:gcpFetch});
assert.equal(gcp.profile,'e2-micro');
assert.equal(gcp.region,'us-central1');
assert.equal(gcp.profileEligible,true);

await assert.rejects(()=>collectCloudAttestation('oci'),/unsupported_cloud_vendor/);
console.log(JSON.stringify({suite:'CLOUD_HOST_ATTESTATION',state:'PASS',benchmarkVendors:['clawcloud','back4app'],gcp:'BLOCKED',modal:'DISQUALIFIED_FINANCIAL',oci:'RETIRED'}));
