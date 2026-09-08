import {runRadarCycle} from './universal-radar-cycle.mjs';
const out=await runRadarCycle();
console.log(JSON.stringify(out,null,2));
if(!out.pass||!out.ledgerOk||out.healthySources<10||out.itemCount<100) process.exit(1);
