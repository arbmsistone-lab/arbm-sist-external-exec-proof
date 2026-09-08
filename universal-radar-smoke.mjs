import fs from 'node:fs';
import {collectAll} from './universal-radar-collector.mjs';
const out=await collectAll();
fs.writeFileSync('universal-radar-smoke.json',JSON.stringify(out,null,2));
console.log(JSON.stringify({sourceCount:out.sourceCount,healthySources:out.healthySources,requiredFailures:out.requiredFailures,itemCount:out.items.length,runs:out.runs.map(r=>({sourceId:r.sourceId,ok:r.ok,count:r.count,error:r.error||null}))},null,2));
process.exit(out.requiredFailures.length?2:0);
