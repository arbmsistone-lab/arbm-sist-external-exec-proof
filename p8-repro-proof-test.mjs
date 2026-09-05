import assert from 'node:assert/strict';
import {verifyP8ReproProof} from './p8-repro-proof.mjs';

const sha='a'.repeat(40), digest='sha256:'+'b'.repeat(64);
const evidence={p8Complete:true,p8Evidence:{runId:77,headSha:sha,successfulAttempts:[1,2],artifactName:'p8-swe-rebench-v2-real-smoke'}};
const attempt=(n)=>({id:77,run_attempt:n,status:'completed',conclusion:'success',head_sha:sha});
const steps=['Generation evidence gate','Run official evaluator on clean public sample task','Freeze hashes','Upload immutable smoke evidence'].map(name=>({name,conclusion:'success'}));
const jobs=()=>({jobs:[{name:'real-smoke',conclusion:'success',head_sha:sha,steps}]});
const attempts={'1':attempt(1),'2':attempt(2)}, jobMap={'1':jobs(),'2':jobs()};
const artifacts={artifacts:[{name:'p8-swe-rebench-v2-real-smoke',digest,expired:false}]};
const agent={validPatch:true,exitCode:0,providerCostUsd:0,goldPatchExposedToAgent:false,sourceCommit:sha};

assert.equal(verifyP8ReproProof(evidence,attempts,jobMap,artifacts,agent).pass,true);
const paid=structuredClone(agent); paid.providerCostUsd=0.01;
assert.ok(verifyP8ReproProof(evidence,attempts,jobMap,artifacts,paid).reasons.includes('P8_PROVIDER_COST_NOT_ZERO'));
const gold=structuredClone(agent); gold.goldPatchExposedToAgent=true;
assert.ok(verifyP8ReproProof(evidence,attempts,jobMap,artifacts,gold).reasons.includes('P8_GOLD_PATCH_FIREWALL_INVALID'));
const bad=structuredClone(attempts); bad['2'].head_sha='c'.repeat(40);
assert.ok(verifyP8ReproProof(evidence,bad,jobMap,artifacts,agent).reasons.includes('P8_ATTEMPT_INVALID:2'));
console.log('p8 reproducibility proof tests: PASS');
