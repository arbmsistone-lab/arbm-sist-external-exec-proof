import assert from 'node:assert/strict';
import {collectCloudAttestation} from './cloud-host-attestation.mjs';

function response(body){return {ok:true,text:async()=>String(body),json:async()=>body};}
function withEnv(values,fn){const old={};for(const [k,v] of Object.entries(values)){old[k]=process.env[k];process.env[k]=v;}return Promise.resolve(fn()).finally(()=>{for(const [k,v] of Object.entries(old)){if(v===undefined)delete process.env[k];else process.env[k]=v;}});}

const modal=await withEnv({MODAL_TASK_ID:'ta-test',ARBM_CPU_CORES:'0.125',ARBM_MEMORY_MIB:'512'},()=>collectCloudAttestation('modal'));
assert.equal(modal.instanceId,'ta-test');
assert.equal(modal.profile,'modal-starter-cpu-0.125-mem-512');
assert.equal(modal.profileEligible,true);
assert.equal(modal.requiresBillingVerification,true);

const modalTooLarge=await withEnv({MODAL_TASK_ID:'ta-bad',ARBM_CPU_CORES:'0.25',ARBM_MEMORY_MIB:'512'},()=>collectCloudAttestation('modal'));
assert.equal(modalTooLarge.profileEligible,false);

const back4app=await withEnv({ARBM_INSTANCE_ID:'b4a-test',ARBM_CPU_CORES:'0.25',ARBM_MEMORY_MIB:'256'},()=>collectCloudAttestation('back4app'));
assert.equal(back4app.instanceId,'b4a-test');
assert.equal(back4app.profile,'back4app-free-container');
assert.equal(back4app.profileEligible,true);

const back4appTooLarge=await withEnv({ARBM_INSTANCE_ID:'b4a-bad',ARBM_CPU_CORES:'0.5',ARBM_MEMORY_MIB:'512'},()=>collectCloudAttestation('back4app'));
assert.equal(back4appTooLarge.profileEligible,false);

const values={'/id':'123456789','/machine-type':'projects/1/machineTypes/e2-micro','/zone':'projects/1/zones/us-central1-a'};
const gcpFetch=async url=>response(values[new URL(url).pathname.replace('/computeMetadata/v1/instance','')]);
const gcp=await collectCloudAttestation('gcp',{fetchImpl:gcpFetch});
assert.equal(gcp.profile,'e2-micro');
assert.equal(gcp.region,'us-central1');
assert.equal(gcp.profileEligible,true);

await assert.rejects(()=>collectCloudAttestation('oci'),/unsupported_cloud_vendor/);
console.log(JSON.stringify({suite:'CLOUD_HOST_ATTESTATION',state:'PASS',vendors:['modal','back4app','gcp'],oci:'RETIRED'}));
