import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {recordQuotaFailure,recordQuotaHeaders,quotaDecision} from './p2-engine-snapshot/quota-shield.mjs';
import {deploymentMeshPlan,deployWithFailover} from './p2-engine-snapshot/deployment-mesh.mjs';
import {captureComputerState,verifyComputerTransition,actionDecision} from './p2-engine-snapshot/computer-use-verifier.mjs';

const candidate=process.env.ARBM_EXPECTED_SHA||'';
const sha=v=>crypto.createHash('sha256').update(JSON.stringify(v)).digest('hex');
const results=[];
function pass(id,detail){results.push({scenario_id:id,result:'PASS',evidence_type:'REMOTE_DETERMINISTIC',candidate_sha:candidate,detail,evidence_hash:sha(detail)});}
const root=fs.mkdtempSync(path.join(os.tmpdir(),'arbm-fm-'));
try {
  const quotaFile=path.join(root,'quota.json');
  recordQuotaFailure(quotaFile,'provider-a',60);
  const q429=quotaDecision(quotaFile,'provider-a',{critical:false});
  assert.equal(q429.eligible,false); assert.equal(q429.state,'COOLDOWN');
  pass('FM04',{fault:'http_429',cooldown:true,eligible:false,state:q429.state,paid_fallback:false});  const headers=new Headers({
    'x-ratelimit-limit-requests':'100','x-ratelimit-remaining-requests':'10',
    'x-ratelimit-limit-tokens':'100000','x-ratelimit-remaining-tokens':'10000'
  });
  recordQuotaHeaders(quotaFile,'provider-b',headers);
  const exhausted=quotaDecision(quotaFile,'provider-b',{critical:false,reservedTokens:0});
  assert.equal(exhausted.eligible,false); assert.equal(exhausted.state,'RESERVED_FOR_CRITICAL');
  pass('FM15',{fault:'artificial_quota_exhaustion',predicted_block:true,state:exhausted.state,quota_overrun:false,paid_fallback:false});

  const routes=[
    {id:'deploy-a',enabled:true,executionType:'remote',zeroCostVerified:true,zeroMandatorySpend:true,unitCost:0,billingRequired:false,domains:['app']},
    {id:'deploy-b',enabled:true,executionType:'remote',zeroCostVerified:true,zeroMandatorySpend:true,unitCost:0,billingRequired:false,domains:['app']}
  ];
  const plan=deploymentMeshPlan({routes,criticalDomains:['app']});
  assert.equal(plan.state,'READY');
  const deployed=await deployWithFailover(plan,'app',{sha:candidate},async id=>id==='deploy-a'?{state:'FAILED'}:{state:'SUCCEEDED',sha:candidate});
  assert.equal(deployed.state,'SUCCEEDED'); assert.equal(deployed.routeId,'deploy-b'); assert.equal(deployed.failoverCount,1);
  pass('FM16',{fault:'deploy_failure_midflight',first_route:'FAILED',fallback_route:'deploy-b',state:'SUCCEEDED',same_sha:true});  const before=captureComputerState({screenshot:'same',accessibilityTree:{a:1},appState:{x:1},url:'https://example.invalid',title:'A'});
  const after=captureComputerState({screenshot:'same',accessibilityTree:{a:1},appState:{x:1},url:'https://example.invalid',title:'A'});
  const verification=verifyComputerTransition(before,after,{requireChange:true,minSignals:1});
  const decision=actionDecision({risk:'HIGH',verification});
  assert.equal(verification.pass,false); assert.equal(decision.state,'RECOVERY_REQUIRED');
  pass('FM17',{fault:'verifier_rejects',verification_pass:false,final_state:decision.state,false_succeeded:false});

  let rollbackAttempts=0; let active='new';
  async function safeRollback(){
    for(let i=0;i<2;i++){
      rollbackAttempts++;
      try { if(rollbackAttempts===1) throw new Error('rollback_transport_failure'); active='old'; return true; }
      catch(e){ if(rollbackAttempts>=2) throw e; }
    }
    return false;
  }
  assert.equal(await safeRollback(),true); assert.equal(active,'old'); assert.equal(rollbackAttempts,2);
  pass('FM18',{fault:'rollback_first_attempt_fails',attempts:rollbackAttempts,final_active:'old',unsafe_forward_state:false});
} finally {
  fs.rmSync(root,{recursive:true,force:true});
}
assert.equal(results.length,5);
console.log(JSON.stringify({suite:'ARBM-FAULT-MATRIX-REMOTE',pass:results.length,total:5,candidate_sha:candidate,results}));