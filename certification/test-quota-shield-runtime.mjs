import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {quotaFile,recordQuotaFailure,quotaDecision,quotaPolicy} from './p2-engine-snapshot/quota-shield.mjs';

const root=fs.mkdtempSync(path.join(os.tmpdir(),'arbm-quota-'));
const file=quotaFile(root);

assert.equal(quotaDecision(file,'missing').eligible,false);
assert.equal(quotaDecision(file,'missing').state,'QUOTA_UNKNOWN');
assert.equal(quotaDecision(file,'missing',{allowUnknownHardStop:true}).eligible,true);

fs.mkdirSync(path.dirname(file),{recursive:true});
fs.writeFileSync(file,JSON.stringify({schema:'arbm-quota-shield-v1',providers:{
  alpha:{provider:'alpha',limitRequests:100,remainingRequests:80,limitTokens:100000,remainingTokens:90000,cooldownUntil:''}
}},null,2));

let d=quotaDecision(file,'alpha',{critical:false,reservedTokens:10000});
assert.equal(d.eligible,true);
assert.equal(d.state,'ALLOW');

d=quotaDecision(file,'alpha',{critical:false,reservedTokens:70000});
assert.equal(d.eligible,false);
assert.equal(d.state,'RESERVED_FOR_CRITICAL');

d=quotaDecision(file,'alpha',{critical:true,reservedTokens:74000});
assert.equal(d.eligible,true);

d=quotaDecision(file,'alpha',{critical:true,reservedTokens:76000});
assert.equal(d.eligible,false);
assert.equal(d.state,'CRITICAL_RESERVE_EXHAUSTED');

recordQuotaFailure(file,'alpha',60);
d=quotaDecision(file,'alpha',{critical:false});
assert.equal(d.eligible,false);
assert.equal(d.state,'COOLDOWN');

assert.equal(quotaPolicy.normalReserve,0.25);
assert.equal(quotaPolicy.criticalReserve,0.15);
console.log('QUOTA_SHIELD_RUNTIME=PASS');
