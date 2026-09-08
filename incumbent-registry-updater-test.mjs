import fs from 'node:fs';
import assert from 'node:assert/strict';
import {updateRegistry} from './incumbent-registry-updater.mjs';
const path='incumbent-registry.json'; const backup=fs.readFileSync(path,'utf8');
try{
  const base={observedAt:'2026-09-08T13:00:00Z',attestationHash:'sha256:test',routes:[]};
  const none=updateRegistry(base);
  assert.equal(none.status,'CONFIGURED_UNATTESTED'); assert.equal(none.usableForReplacementProposal,false);
  const reg=JSON.parse(fs.readFileSync(path,'utf8')); reg.domains['ai-providers'].active={id:'old',version:'v1',artifactSha256:'sha256:old',activatedAt:'x',zeroSpendVerified:true}; fs.writeFileSync(path,JSON.stringify(reg,null,2));
  const ambiguous=updateRegistry({...base,attestationHash:'sha256:amb',routes:[{state:'VERIFIED',identity:{id:'a'}},{state:'VERIFIED',identity:{id:'b'}}]});
  assert.equal(ambiguous.status,'AMBIGUOUS'); assert.equal(ambiguous.active.id,'old');
  const one=updateRegistry({...base,attestationHash:'sha256:one',routes:[{state:'VERIFIED',identity:{id:'free-primary',version:'m',artifactSha256:'sha256:a',activatedAt:'x',zeroSpendVerified:true}}]});
  assert.equal(one.status,'VERIFIED'); assert.equal(one.active.id,'free-primary'); assert.equal(one.usableForReplacementProposal,true);
  console.log('INCUMBENT_REGISTRY_UPDATER_PASS');
} finally { fs.writeFileSync(path,backup); }
