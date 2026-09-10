import fs from 'node:fs';
import {captureComputerState,verifyComputerTransition,actionDecision} from './computer-use-verifier.mjs';
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const before=captureComputerState(input.before||{});
const after=captureComputerState(input.after||{});
const verification=verifyComputerTransition(before,after,input.verify||{minSignals:1});
const decision=actionDecision({risk:input.risk||'LOW',verification});
process.stdout.write(JSON.stringify({before,after,verification,decision}));