import {runRadarCycleV2} from './universal-radar-cycle-v2.mjs';
const r=await runRadarCycleV2();
console.log(JSON.stringify(r,null,2));
if(!r.pass||!r.ledgerOk) process.exit(2);
