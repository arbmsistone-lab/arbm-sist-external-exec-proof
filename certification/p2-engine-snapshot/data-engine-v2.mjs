import {analyzeTable} from './data-engine.mjs';
function parseCsv(text=''){const lines=String(text).trim().split(/\r?\n/).filter(Boolean);if(!lines.length)return [];const head=lines[0].split(',').map(x=>x.trim());return lines.slice(1).map(line=>Object.fromEntries(line.split(',').map((v,i)=>[head[i],v.trim()])));}
export function ingestDataSource({kind='table',data=null,name=''}={}){
  const k=String(kind).toLowerCase();let rows=[];
  if(k==='table'||k==='database')rows=Array.isArray(data)?data:[];
  else if(k==='spreadsheet')rows=typeof data==='string'?parseCsv(data):Array.isArray(data)?data:[];
  else if(k==='document'){const sections=Array.isArray(data)?data:[String(data||'')];rows=sections.map((text,i)=>({section:i+1,text:String(text),length:String(text).length}));}
  else throw new Error('unsupported_data_source:'+k);
  const report=analyzeTable(rows);return {...report,source:{kind:k,name:String(name),records:rows.length}};
}
export function buildDataReport(sources=[]){const reports=sources.map(ingestDataSource);return {schema:'arbm-data-engine-v2',state:reports.length?'READY':'BLOCKED',sources:reports,sourceKinds:[...new Set(reports.map(r=>r.source.kind))],totalRows:reports.reduce((n,r)=>n+r.rowCount,0)};}
export function dataV2Gate(report={}){const needed=['table','spreadsheet','database','document'];const blockers=[];if(report.state!=='READY')blockers.push('report_not_ready');for(const k of needed)if(!report.sourceKinds?.includes(k))blockers.push('missing:'+k);return {pass:blockers.length===0,blockers};}
