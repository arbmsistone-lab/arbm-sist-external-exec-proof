import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
const p=new URL('./global-release-readiness.json',import.meta.url);
const d=JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const quorum=JSON.parse(execFileSync(process.execPath,['certification/provider-operational-quorum.mjs'],{encoding:'utf8'}));
const passing=new Set(['PASS','CERTIFIED']);
const blockers=[];
if(d?.policy?.zeroSpendHard!==true) blockers.push('policy:zeroSpendHard');
if(d?.policy?.heavyExecution!=='REMOTE_ONLY') blockers.push('policy:heavyExecution');
if(d?.policy?.failClosed!==true) blockers.push('policy:failClosed');
for(const [name,g] of Object.entries(d.gates??{})){
  if(name==='providerOperationalQuorum') continue;
  if(!passing.has(g.status)) blockers.push(`${name}:${g.status||'MISSING'}`);
}
if(!quorum.pass) blockers.push(`providerOperationalQuorum:${quorum.activeIndependentDomains}/${quorum.requiredIndependentDomains}`);
const report={schema:'arbm-global-release-gate-v1',failClosed:true,pass:blockers.length===0,blockers,providerQuorum:quorum};
console.log(JSON.stringify(report,null,2));
if(process.env.ARBM_ENFORCE_GLOBAL_RELEASE==='1'&&!report.pass) process.exit(1);
