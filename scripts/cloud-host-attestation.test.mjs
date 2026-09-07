import assert from 'node:assert/strict';
import {collectCloudAttestation} from './cloud-host-attestation.mjs';

function response(body){return {ok:true,text:async()=>String(body),json:async()=>body};}
const ociFetch=async()=>response({id:'ocid1.instance.test',region:'us-ashburn-1',shape:'VM.Standard.A1.Flex',shapeConfig:{ocpus:4,memoryInGB:24}});
const oci=await collectCloudAttestation('oci',{fetchImpl:ociFetch});
assert.equal(oci.instanceId,'ocid1.instance.test');
assert.equal(oci.profileEligible,true);
assert.equal(oci.requiresBillingVerification,true);

const badOciFetch=async()=>response({id:'bad',region:'x',shape:'VM.Standard.A1.Flex',shapeConfig:{ocpus:5,memoryInGB:30}});
const badOci=await collectCloudAttestation('oci',{fetchImpl:badOciFetch});
assert.equal(badOci.profileEligible,false);

const values={
  '/id':'123456789',
  '/machine-type':'projects/1/machineTypes/e2-micro',
  '/zone':'projects/1/zones/us-central1-a'
};
const gcpFetch=async url=>response(values[new URL(url).pathname.replace('/computeMetadata/v1/instance','')]);
const gcp=await collectCloudAttestation('gcp',{fetchImpl:gcpFetch});
assert.equal(gcp.profile,'e2-micro');
assert.equal(gcp.region,'us-central1');
assert.equal(gcp.profileEligible,true);
assert.equal(gcp.requiresBillingVerification,true);

console.log(JSON.stringify({suite:'CLOUD_HOST_ATTESTATION',state:'PASS'}));
