import crypto from 'node:crypto';
const sha=x=>'sha256:'+crypto.createHash('sha256').update(String(x)).digest('hex');
export function promotionHashOf({domain,previous,next,proposalHash,evidenceHash,at}){
  return sha(JSON.stringify({domain,previous,challengerIdentity:next,proposalHash,evidenceHash,now:at}));
}
export function rollbackHashOf({domain,promotionHash,failed,restored,reason,evidenceHash,at}){
  return sha(JSON.stringify({domain,promotionHash,failed,restored,reason,evidenceHash,now:at}));
}
export const sameJson=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
export function validPromotionHistory(domain,h){
  if(!h||h.type!=='PROMOTION') return false;
  return h.promotionHash===promotionHashOf({domain,previous:h.previous,next:h.next,proposalHash:h.proposalHash,evidenceHash:h.evidenceHash,at:h.at});
}
export function validRollbackHistory(domain,h,promotion){
  if(!h||h.type!=='ROLLBACK'||!promotion) return false;
  if(!sameJson(h.failed,promotion.next)||!sameJson(h.restored,promotion.previous)) return false;
  return h.rollbackHash===rollbackHashOf({domain,promotionHash:h.promotionHash,failed:h.failed,restored:h.restored,reason:h.reason,evidenceHash:h.evidenceHash,at:h.at});
}
