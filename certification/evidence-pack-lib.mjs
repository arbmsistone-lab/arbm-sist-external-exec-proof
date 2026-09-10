import crypto from 'node:crypto';

export function canonical(value){
  if(Array.isArray(value)) return value.map(canonical);
  if(value && typeof value==='object') return Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])]));
  return value;
}
export function sha256(value){
  const text=typeof value==='string'?value:JSON.stringify(canonical(value));
  return crypto.createHash('sha256').update(text).digest('hex');
}
export function buildPack({certifiedSha,g1Baseline,members,metadata={}}){
  const normalized=members.map(m=>({name:String(m.name),sourceRun:String(m.sourceRun||''),content:canonical(m.content),sha256:sha256(m.content)}));
  const body={schema:'arbm-final-certification-evidence-v1',certifiedSha:String(certifiedSha),g1Baseline:String(g1Baseline),metadata:canonical(metadata),members:normalized};
  return {...body,manifestSha256:sha256(body)};
}
export function verifyPack(pack){
  if(!pack || pack.schema!=='arbm-final-certification-evidence-v1') return false;
  if(!Array.isArray(pack.members)||!pack.members.length) return false;
  if(pack.members.some(m=>sha256(m.content)!==m.sha256)) return false;
  const {manifestSha256,...body}=pack;
  return /^[0-9a-f]{64}$/.test(String(manifestSha256||'')) && sha256(body)===manifestSha256;
}