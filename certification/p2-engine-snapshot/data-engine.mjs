export function normalizeTable(input=[]){
  if(!Array.isArray(input))throw new Error('table_array_required');
  if(!input.length)return {columns:[],rows:[]};
  const rows=input.map(x=>({...x})),columns=[...new Set(rows.flatMap(x=>Object.keys(x)))];
  return {columns,rows:rows.map(r=>Object.fromEntries(columns.map(c=>[c,r[c]??null])))};
}
export function analyzeTable(input=[]){
  const table=normalizeTable(input),numeric={};
  for(const c of table.columns){const vals=table.rows.map(r=>Number(r[c])).filter(Number.isFinite);if(vals.length)numeric[c]={count:vals.length,sum:vals.reduce((a,b)=>a+b,0),min:Math.min(...vals),max:Math.max(...vals),avg:vals.reduce((a,b)=>a+b,0)/vals.length};}
  return {schema:'arbm-data-report-v1',rowCount:table.rows.length,columnCount:table.columns.length,columns:table.columns,numeric,table};
}
export function dataGate(report={}){
  const blockers=[];if(!report.schema)blockers.push('report_required');if(!Array.isArray(report.table?.rows))blockers.push('table_required');
  return {pass:blockers.length===0,blockers};
}
