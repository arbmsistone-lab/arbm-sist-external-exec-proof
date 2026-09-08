import fs from 'node:fs';
import {appendEvidence} from './universal-radar-evidence-ledger.mjs';
const path='incumbent-registry.json';
const load=()=>JSON.parse(fs.readFileSync(path,'utf8'));
function atomicWriteJson(target,value){const tmp=target+'.tmp-'+process.pid;const fd=fs.openSync(tmp,'w');try{fs.writeFileSync(fd,JSON.stringify(value,null,2));fs.fsyncSync(fd);}finally{fs.closeSync(fd);}fs.renameSync(tmp,target);}
export function updateRegistry(attestation,domain='ai-providers'){
  const reg=load(); const slot=reg.domains?.[domain];
  if(!slot) throw new Error('INCUMBENT_DOMAIN_UNKNOWN:'+domain);
  const verified=(attestation.routes||[]).filter(x=>x.state==='VERIFIED');
  const previous=slot.active||null; const now=attestation.observedAt||new Date().toISOString();
  if(verified.length===1){
    const winner=verified[0];
    slot.status='VERIFIED'; slot.active=winner.identity;
    slot.attestationHash=attestation.attestationHash; slot.verifiedAt=now;
    slot.usableForReplacementProposal=true;
  }else{
    slot.status=verified.length>1?'AMBIGUOUS':'CONFIGURED_UNATTESTED';
    slot.usableForReplacementProposal=false;
    slot.lastAttestationHash=attestation.attestationHash;
    slot.lastAttestationAt=now;
    if(previous) slot.active=previous;
  }
  reg.updatedAt=now; atomicWriteJson(path,reg);
  const ev=appendEvidence({type:'INCUMBENT_ATTESTATION',domain,status:slot.status,verifiedCount:verified.length,usableForReplacementProposal:slot.usableForReplacementProposal,attestationHash:attestation.attestationHash});
  return {domain,status:slot.status,active:slot.active,usableForReplacementProposal:slot.usableForReplacementProposal,evidenceSequence:ev.sequence,evidenceHash:ev.entryHash};
}
