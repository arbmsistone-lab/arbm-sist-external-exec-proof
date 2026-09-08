import fs from 'node:fs';
import {evaluateReplacementProposal} from './replacement-proposal-gate.mjs';
const path='incumbent-registry.json'; const backup=fs.readFileSync(path,'utf8');
const goodResult={grade:'replacementGrade',decision:'REPLACEMENT_CANDIDATE',replacementApplied:false,gates:{sampleOk:true,pairedOk:true,integrityOk:true}};
const challenger={id:'candidate-x',version:'1',artifactSha256:'sha256:'+'b'.repeat(64),activatedAt:'2026-09-08T00:00:00Z',zeroSpendVerified:true};
try{
  let r=evaluateReplacementProposal({domain:'coding-models',challengerResult:goodResult,challengerIdentity:challenger});
  if(r.approved||!r.reasons.includes('INCUMBENT_NOT_VERIFIED')) throw new Error('UNVERIFIED_INCUMBENT_ALLOWED');
  const reg=JSON.parse(backup); reg.domains['coding-models']={status:'VERIFIED',active:{id:'incumbent-a',version:'7',artifactSha256:'sha256:'+'a'.repeat(64),activatedAt:'2026-09-01T00:00:00Z',zeroSpendVerified:true}}; fs.writeFileSync(path,JSON.stringify(reg,null,2));
  r=evaluateReplacementProposal({domain:'coding-models',challengerResult:goodResult,challengerIdentity:challenger});
  if(!r.approved||r.action!=='OPEN_P9_REPLACEMENT_PROPOSAL') throw new Error('STALE_REGISTRY_SNAPSHOT');
  const mod={evaluateReplacementProposal};
  const paid={...challenger,zeroSpendVerified:false};
  if(mod.evaluateReplacementProposal({domain:'coding-models',challengerResult:goodResult,challengerIdentity:paid}).approved) throw new Error('PAID_CHALLENGER_ALLOWED');
  console.log('REPLACEMENT_PROPOSAL_GATE_PASS');
} finally {fs.writeFileSync(path,backup);}
