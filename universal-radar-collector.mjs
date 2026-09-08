import fs from 'node:fs';
const cfg=JSON.parse(fs.readFileSync('universal-radar-sources.json','utf8'));
const max=cfg.maxItemsPerSource||60;
const text=(v)=>String(v??'').replace(/\s+/g,' ').trim();
const clip=(v,n=500)=>text(v).slice(0,n);
async function fetchText(url,timeoutMs){
  const r=await fetch(url,{headers:{'user-agent':'ARBM-SIST-Universal-Radar/1.0','accept':'application/json, application/atom+xml, application/rss+xml, text/xml, */*'},signal:AbortSignal.timeout(timeoutMs)});
  if(!r.ok) throw new Error(`HTTP_${r.status}`);
  return {body:await r.text(),contentType:r.headers.get('content-type')||''};
}
function xmlEntries(xml,tag){
  const re=new RegExp(`<${tag}\\b[^>]*>([\\s\\S]*?)<\\/${tag}>`,'gi');
  return [...xml.matchAll(re)].map(m=>m[1]);
}
function xmlField(block,name){
  const m=block.match(new RegExp(`<${name}\\b[^>]*>([\\s\\S]*?)<\\/${name}>`,'i'));
  return m?clip(m[1].replace(/<!\[CDATA\[|\]\]>/g,'').replace(/<[^>]+>/g,' '),1000):'';
}
function parseJsonSource(src,body){
  const j=JSON.parse(body); let rows=[];
  if(src.kind==='json') rows=Array.isArray(j)?j:[];
  else if(src.kind==='json-data') rows=Array.isArray(j?.data)?j.data:[];
  else if(src.kind==='npm-search') rows=(j?.objects||[]).map(x=>x.package||{});
  else if(src.kind==='crates') rows=j?.crates||[];
  else if(src.kind==='github-releases') rows=Array.isArray(j)?j:[];
  else if(src.kind==='cisa-kev') rows=j?.vulnerabilities||[];
  return rows.slice(0,max).map((x,i)=>({
    sourceId:src.id, domain:src.domain, primarySource:src.primary===true,
    externalId:clip(x.id||x.name||x.slug||x.cveID||x.tag_name||`${src.id}-${i}`,180),
    name:clip(x.name||x.id||x.package?.name||x.cveID||x.tag_name||'unknown',240),
    summary:clip(x.description||x.summary||x.body||x.short_description||x.vulnerabilityName||'',1000),
    url:clip(x.html_url||x.url||x.homepage||x.repository||x.link||'',1000),
    updatedAt:clip(x.lastModified||x.updated_at||x.created_at||x.published_at||x.dateAdded||'',100),
    rawMeta:{downloads:x.downloads,likes:x.likes,version:x.version,pricing:x.pricing,architecture:x.architecture}
  }));
}
function parseXmlSource(src,body){
  const tag=src.kind==='rss'?'item':'entry';
  return xmlEntries(body,tag).slice(0,max).map((b,i)=>({
    sourceId:src.id, domain:src.domain, primarySource:src.primary===true,
    externalId:xmlField(b,'id')||xmlField(b,'guid')||`${src.id}-${i}`,
    name:xmlField(b,'title')||'unknown', summary:xmlField(b,'summary')||xmlField(b,'description'),
    url:xmlField(b,'link'), updatedAt:xmlField(b,'updated')||xmlField(b,'published')||xmlField(b,'pubDate'), rawMeta:{}
  }));
}
export async function collectSource(src){
  const started=Date.now();
  try{
    const {body}=await fetchText(src.url,src.timeoutMs||cfg.defaultTimeoutMs||12000);
    const items=(src.kind==='rss'||src.kind==='atom')?parseXmlSource(src,body):parseJsonSource(src,body);
    return {sourceId:src.id,ok:true,latencyMs:Date.now()-started,count:items.length,items};
  }catch(e){
    return {sourceId:src.id,ok:false,bestEffort:src.bestEffort===true,latencyMs:Date.now()-started,count:0,error:clip(e?.message||e,300),items:[]};
  }
}
export async function collectAll(){
  const runs=await Promise.all(cfg.sources.map(collectSource));
  const requiredFailures=runs.filter(r=>!r.ok&&!r.bestEffort);
  const items=runs.flatMap(r=>r.items);
  return {schema:'arbm-universal-radar-collection-v1',observedAt:new Date().toISOString(),sourceCount:runs.length,healthySources:runs.filter(r=>r.ok).length,requiredFailures:requiredFailures.map(r=>r.sourceId),items,runs};
}
if(import.meta.url===`file://${process.argv[1].replace(/\\/g,'/')}`){
  const out=await collectAll();
  process.stdout.write(JSON.stringify(out));
  process.exit(out.requiredFailures.length?2:0);
}
