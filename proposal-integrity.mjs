import crypto from 'node:crypto';
export const sha=x=>'sha256:'+crypto.createHash('sha256').update(String(x)).digest('hex');
export const digest=x=>/^sha256:[0-9a-f]{64}$/i.test(String(x||''));
export const challengerResultHashOf=result=>sha(JSON.stringify(result));
export function proposalHashOf({domain,incumbentIdentity,challengerIdentity,challengerResultHash}){
  return sha(JSON.stringify({
    domain,
    incumbent:incumbentIdentity,
    challengerIdentity,
    challengerResultHash
  }));
}
export function validProposalHash(proposal){
  if(!proposal||!digest(proposal.challengerResultHash)) return false;
  return proposal.proposalHash===proposalHashOf(proposal);
}
