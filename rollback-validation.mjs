import {appendEvidence,findEvidence,verifyLedger,validLedgerHash} from './universal-radar-evidence-ledger.mjs';
export function registerRollbackValidation({domain,promotionHash,reason,validationResult}){
  const reasons=[];
  if(!String(domain||'').trim()) reasons.push('DOMAIN_REQUIRED');
  if(!/^sha256:[0-9a-f]{64}$/i.test(String(promotionHash||''))) reasons.push('PROMOTION_HASH_INVALID');
  if(!String(reason||'').trim()) reasons.push('ROLLBACK_REASON_REQUIRED');
  if(validationResult?.status!=='PASS') reasons.push('ROLLBACK_VALIDATION_NOT_PASS');
  if(!validLedgerHash(validationResult?.evidenceHash)) reasons.push('ROLLBACK_SOURCE_HASH_INVALID');
  const src=findEvidence(validationResult?.evidenceHash); const payload=src?.entry?.payload;
  if(!src.ok||payload?.type!=='ROLLBACK_VALIDATION_SOURCE'||payload?.status!=='PASS'||payload?.domain!==domain||payload?.promotionHash!==promotionHash) reasons.push('ROLLBACK_SOURCE_MISMATCH');
  const ledger=verifyLedger(); if(!ledger.ok) reasons.push('EVIDENCE_LEDGER_INVALID');
  if(reasons.length) return {validated:false,reasons};
  const entry=appendEvidence({type:'ROLLBACK_VALIDATED',domain,promotionHash,reason,status:'PASS',sourceHash:validationResult.evidenceHash});
  return {validated:true,status:'PASS',domain,promotionHash,reason,evidenceHash:entry.entryHash};
}
