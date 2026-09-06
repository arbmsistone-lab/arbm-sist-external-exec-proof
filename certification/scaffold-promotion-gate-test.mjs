import assert from 'node:assert/strict';
import { evaluateScaffoldPromotion } from './scaffold-promotion-gate.mjs';

const comparability = {sameModel:true,sameTaskSet:true,sameBudget:true,sameHarness:true,sameVerifier:true};
const regression = {allExistingGatesPass:true,newP0:0,newP1:0,newP2:0};
const trials = rewards => rewards.flatMap((row, ti) => row.map((reward, ri) => ({task:`t${ti+1}`,rep:ri+1,reward,exception:false})));
const modes = (a,b,c) => ({premature_completion:a,missing_required_output:b,no_final_verification:c});

const gainCase = evaluateScaffoldPromotion({comparability,regression,
  baselineTrials:trials([[0,0,0],[0,0,0],[0,0,0]]),
  candidateTrials:trials([[1,1,1],[1,1,1],[0,0,0]]),
  failureModes:{baseline:modes(0,0,0),candidate:modes(0,0,0)}});
assert.equal(gainCase.pass,true);
assert.equal(gainCase.reproducibleGain,true);

const taskRegressionCase = evaluateScaffoldPromotion({comparability,regression,
  baselineTrials:trials([[0,0,0],[0,0,0],[1,1,1]]),
  candidateTrials:trials([[1,1,1],[1,1,1],[0,0,0]]),
  failureModes:{baseline:modes(0,0,0),candidate:modes(0,0,0)}});
assert.equal(taskRegressionCase.reproducibleGain,true);
assert.equal(taskRegressionCase.zeroRegression,false);
assert.equal(taskRegressionCase.pass,false);

const repairCase = evaluateScaffoldPromotion({comparability,regression,
  baselineTrials:trials([[0,0,0],[0,0,0],[0,0,0]]),
  candidateTrials:trials([[0,0,0],[0,0,0],[0,0,0]]),
  failureModes:{baseline:modes(3,3,3),candidate:modes(0,0,0)}});
assert.equal(repairCase.pass,true);
assert.equal(repairCase.failureModeElimination,true);

const tieCase = evaluateScaffoldPromotion({comparability,regression,
  baselineTrials:trials([[0,0,0],[0,0,0],[0,0,0]]),
  candidateTrials:trials([[0,0,0],[0,0,0],[0,0,0]]),
  failureModes:{baseline:modes(0,0,0),candidate:modes(0,0,0)}});
assert.equal(tieCase.pass,false);
console.log('SCAFFOLD_PROMOTION_GATE_TEST_PASS');
