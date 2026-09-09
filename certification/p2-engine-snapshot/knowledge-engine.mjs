import crypto from 'node:crypto';
const sha=s=>crypto.createHash('sha256').update(String(s)).digest('hex');
const words=s=>new Set(String(s).toLowerCase().match(/[a-z0-9\u00c0-\u024f_]+/g)||[]);
export class KnowledgeEngine{
  constructor(){this.docs=new Map();this.projects=new Map();}
  add({projectId='',id='',text='',metadata={}}={}){
    if(!projectId||!String(text).trim())throw new Error('project_and_text_required');
    const digest=sha(text),key=projectId+':'+digest;if(this.docs.has(key))return {...this.docs.get(key),deduplicated:true};
    const row={id:String(id||digest.slice(0,16)),projectId:String(projectId),text:String(text),metadata:{...metadata},sha256:digest};
    this.docs.set(key,row);if(!this.projects.has(projectId))this.projects.set(projectId,[]);this.projects.get(projectId).push(key);return {...row,deduplicated:false};
  }
  search({projectId='',query='',limit=5}={}){
    const q=words(query),keys=this.projects.get(String(projectId))||[];
    return keys.map(k=>this.docs.get(k)).map(d=>{const w=words(d.text);let hit=0;for(const x of q)if(w.has(x))hit++;return {...d,score:q.size?hit/q.size:0};}).filter(x=>x.score>0).sort((a,b)=>b.score-a.score).slice(0,Math.max(1,Number(limit)||5));
  }
  memory(projectId){return (this.projects.get(String(projectId))||[]).map(k=>({...this.docs.get(k)}));}
}
export function knowledgeGate(engine,projectId){const memory=engine?.memory?.(projectId)||[];return {pass:memory.length>0,documents:memory.length,deduplicated:new Set(memory.map(x=>x.sha256)).size===memory.length};}
