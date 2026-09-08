import fs from 'node:fs';
import crypto from 'node:crypto';
const policy=JSON.parse(fs.readFileSync('challenger-policy.json','utf8'));
const sha=x=>'sha256:'+crypto.createHash('sha256').update(String(x)).digest('hex');
const pct=(a,b)=>b?100*a/b:0;
const median=x=>{const a=[...x].sort((p,q)=>p-q); if(!a.length)return null; const m=Math.floor(a.length/2); return a.length%2?a[m]:(a[m-1]+a[m])/2;};
const p95=x=>{const a=[...x].sort((p,q)=>p-q); if(!a.length)return null; return a[Math.min(a.length-1,Math.ceil(a.length*.95)-1)];};
function normalizeRun(r={}){
  return {id:String(r.id||''),pass:r.pass===true,integrity:r.integrity!==false,latencyMs:Number(r.latencyMs||0),criticalRegression:r.criticalRegression===true};
}
export function comparePaired({incumbent,candidate,candidateMeta={},grade='microShadow'}){
  const inc=(incumbent||[]).map(normalizeRun), cand=(candidate||[]).map(normalizeRun);
  const byInc=new Map(inc.map(x=>[x.id,x])), byCand=new Map(cand.map(x=>[x.id,x]));
  const ids=[...new Set([...byInc.keys(),...byCand.keys()])].filter(Boolean);
  const paired=ids.filter(id=>byInc.has(id)&&byCand.has(id)); let wins=0,losses=0,ties=0;
  for(const id of paired){const a=byInc.get(id),b=byCand.get(id); if(b.pass&&!a.pass)wins++; else if(a.pass&&!b.pass)losses++; else ties++;}
  const incPass=paired.filter(id=>byInc.get(id).pass).length, candPass=paired.filter(id=>byCand.get(id).pass).length;
  const margin=pct(candPass-incPass,paired.length); const cfg=policy[grade]||policy.microShadow;
  const integrity=paired.every(id=>byInc.get(id).integrity&&byCand.get(id).integrity);
  const noCritical=paired.every(id=>!byCand.get(id).criticalRegression);
  const zeroSpend=candidateMeta.zeroSpendVerified===true, primary=candidateMeta.primaryEvidence===true;
  const artifactHash=sha(JSON.stringify({paired,inc,cand,candidateMeta,grade}));
  const sampleOk=paired.length>=Number(cfg.minimumSamples||4);
  const pairedOk=grade!=='replacementGrade'||policy.replacementGrade.requireAllPaired!==true||(paired.length===inc.length&&paired.length===cand.length);
  const qualityOk=grade==='replacementGrade'?margin>=-Number(policy.replacementGrade.maxNonInferiorityMarginPp||2):candPass>=incPass;
  const integrityOk=grade!=='replacementGrade'||policy.replacementGrade.requireEvaluatorIntegrity!==true||integrity;
  const costOk=grade!=='replacementGrade'||policy.replacementGrade.requireKnownZeroCost!==true||zeroSpend;
  const primaryOk=grade!=='replacementGrade'||policy.replacementGrade.requirePrimaryEvidence!==true||primary;
  const criticalOk=grade!=='replacementGrade'||policy.replacementGrade.requireNoCriticalRegression!==true||noCritical;
  const allGates=sampleOk&&pairedOk&&qualityOk&&integrityOk&&costOk&&primaryOk&&criticalOk;
  const candLat=paired.map(id=>byCand.get(id).latencyMs), incLat=paired.map(id=>byInc.get(id).latencyMs);
  let decision='REJECT';
  if(grade==='microShadow'&&sampleOk&&integrity&&noCritical&&candPass>=incPass) decision='ADVANCE_TO_REPLACEMENT_GRADE';
  if(grade==='replacementGrade'&&allGates) decision=margin>0||wins>losses?'REPLACEMENT_CANDIDATE':'NON_INFERIOR_CANDIDATE';
  return {
    schema:'arbm-comparative-challenger-result-v1',grade,decision,replacementApplied:false,
    samples:{paired:paired.length,incumbent:inc.length,candidate:cand.length},
    quality:{incumbentPass:incPass,candidatePass:candPass,incumbentRate:Number(pct(incPass,paired.length).toFixed(3)),candidateRate:Number(pct(candPass,paired.length).toFixed(3)),differencePp:Number(margin.toFixed(3)),wins,losses,ties},
    latency:{incumbentMedianMs:median(incLat),candidateMedianMs:median(candLat),incumbentP95Ms:p95(incLat),candidateP95Ms:p95(candLat)},
    gates:{sampleOk,pairedOk,qualityOk,integrityOk,costOk,primaryOk,criticalOk,zeroSpendVerified:zeroSpend,primaryEvidence:primary},
    artifactHash
  };
}
