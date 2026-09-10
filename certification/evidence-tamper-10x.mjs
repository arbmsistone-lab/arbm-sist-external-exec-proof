import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {buildPack,verifyPack} from './evidence-pack-lib.mjs';

const certifiedSha=process.env.ARBM_EXPECTED_SHA||'';
const members=[
  {name:'code-sha',sourceRun:'git',content:{sha:certifiedSha}},
  {name:'log',sourceRun:'34420014060',content:{line:'fault matrix remote PASS'}},
  {name:'test-result',sourceRun:'34420014060',content:{pass:5,total:5}},
  {name:'migration-ref',sourceRun:'supabase',content:{name:'add_storage_replica_contract_v1'}},
  {name:'timestamp',sourceRun:'control-plane',content:{utc:'2026-09-10T00:09:00Z'}},
  {name:'provider-result',sourceRun:'34415106977',content:{from:'circleci',to:'github',state:'SUCCEEDED'}},
  {name:'fault-matrix',sourceRun:'registry',content:{pass:29,total:29}},
  {name:'artifact',sourceRun:'34420014060',content:{digest:'sha256:021b418e30769d3d8e1dd7bbf2527fc60813b16b4bcae46d6946ae276f49f288'}},
  {name:'g1-baseline',sourceRun:'g1-10x',content:{sha:'bdf537528365058d1c3f46649ed92aa0ce5ae99d',pass:'10/10'}},
  {name:'p2-e2e',sourceRun:'p2-10x',content:{sha:'e3efbb73bf413829a631768ed464c06b66ccc48e',pass:'10/10'}}
];
const pack=buildPack({certifiedSha,g1Baseline:'bdf537528365058d1c3f46649ed92aa0ce5ae99d',members,metadata:{zeroSpend:true,heavyLocal:0}});
assert.equal(verifyPack(pack),true);const mutations=[
  p=>p.members[0].content.sha='0'.repeat(40),
  p=>p.members[1].content.line+=' TAMPER',
  p=>p.members[2].content.pass=4,
  p=>p.manifestSha256='0'.repeat(64),
  p=>p.members[7].content.digest='sha256:'+'0'.repeat(64),
  p=>p.members[3].content.name='wrong_migration',
  p=>p.members[4].content.utc='2099-01-01T00:00:00Z',
  p=>p.members[5].content.state='FAILED',
  p=>p.members[6].content.pass=28,
  p=>p.members[9].sha256='f'.repeat(64)
];
let detected=0;
for(const mutate of mutations){
  const copy=structuredClone(pack); mutate(copy);
  if(!verifyPack(copy)) detected++;
}
assert.equal(detected,10);
const report={scenario_id:'FM30',result:'PASS',tamper_attempts:10,detected,undetected:10-detected,candidate_sha:certifiedSha,base_manifest_sha256:pack.manifestSha256};
const out=process.env.ARBM_EVIDENCE_OUT||'certification/evidence/fm30-tamper-report.json';
fs.mkdirSync(path.dirname(out),{recursive:true}); fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));