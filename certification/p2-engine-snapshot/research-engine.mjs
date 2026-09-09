import crypto from 'node:crypto';
const sha=v=>crypto.createHash('sha256').update(JSON.stringify(v??null)).digest('hex');
export function buildResearchReport({question='',sources=[]}={}){
  if(!String(question).trim())throw new Error('question_required');
  const clean=sources.map((s,i)=>({id:String(s.id||`S${i+1}`),title:String(s.title||''),url:String(s.url||''),claim:String(s.claim||''),retrievedAt:String(s.retrievedAt||'')})).filter(s=>s.url&&s.claim);
  if(!clean.length)return {state:'BLOCKED',reason:'sources_required',citations:[],evidence:[]};
  const dedup=[...new Map(clean.map(s=>[s.url+'|'+s.claim,s])).values()];
  const citations=dedup.map(s=>({id:s.id,url:s.url,title:s.title}));
  const evidence=dedup.map(s=>({sourceId:s.id,claim:s.claim,sha256:sha(s)}));
  return {schema:'arbm-research-v1',state:'SUCCEEDED',question:String(question),citations,evidence,sourceCount:dedup.length,evidenceSha256:sha({question,citations,evidence})};
}
export function researchGate(report={}){
  const blockers=[];
  if(report.state!=='SUCCEEDED')blockers.push('research_not_succeeded');
  if(!report.citations?.length)blockers.push('citations_required');
  if(!report.evidence?.length)blockers.push('evidence_required');
  if(report.citations?.some(x=>!x.url))blockers.push('source_url_required');
  return {pass:blockers.length===0,blockers};
}
