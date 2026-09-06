import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const trials = rewards => rewards.flatMap((row, ti) => row.map((reward, ri) => ({task:`t${ti+1}`,rep:ri+1,reward,exception:false})));
const evidence = {
  comparability:{sameModel:true,sameTaskSet:true,sameBudget:true,sameHarness:true,sameVerifier:true},
  regression:{allExistingGatesPass:true,newP0:0,newP1:0,newP2:0},
  baselineTrials:trials([[0,0,0],[0,0,0],[0,0,0]]),
  candidateTrials:trials([[1,1,1],[1,1,1],[0,0,0]]),
  failureModes:{baseline:{},candidate:{}}
};
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'arbm-scaffold-gate-'));
const file = path.join(dir, 'evidence.json');
fs.writeFileSync(file, JSON.stringify(evidence));
const out = execFileSync(process.execPath, ['certification/scaffold-promotion-gate.mjs', file], {encoding:'utf8'});
const result = JSON.parse(out);
if (!result.pass || !result.reproducibleGain || !result.zeroRegression) throw new Error('cli_gate_expected_pass');
fs.rmSync(dir, {recursive:true, force:true});
console.log('SCAFFOLD_PROMOTION_CLI_TEST_PASS');
