import fs from 'node:fs';
import path from 'node:path';
import {buildPack,verifyPack,sha256} from './evidence-pack-lib.mjs';

const inputPath=process.env.ARBM_FINAL_INPUT;
const outPath=process.env.ARBM_FINAL_OUTPUT||'certification/evidence/ARBM-SIST-FINAL-CERTIFICATION-EVIDENCE.json';
if(!inputPath) throw new Error('ARBM_FINAL_INPUT_required');
const input=JSON.parse(fs.readFileSync(inputPath,'utf8'));
if(!input.certifiedSha || !Array.isArray(input.members) || input.members.length===0) throw new Error('final_evidence_input_invalid');
const pack=buildPack({
  certifiedSha:input.certifiedSha,
  g1Baseline:input.g1Baseline,
  members:input.members,
  metadata:input.metadata||{}
});
if(!verifyPack(pack)) throw new Error('final_evidence_integrity_failed');
fs.mkdirSync(path.dirname(outPath),{recursive:true});
fs.writeFileSync(outPath,JSON.stringify(pack,null,2)+'\n');
const digest=sha256(fs.readFileSync(outPath,'utf8'));
fs.writeFileSync(outPath+'.sha256',`${digest}  ${path.basename(outPath)}\n`);
console.log(JSON.stringify({state:'PASS',certifiedSha:pack.certifiedSha,members:pack.members.length,manifestSha256:pack.manifestSha256,fileSha256:digest,outPath}));