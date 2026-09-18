"""Fail-closed multi-AI incident consensus for OSWorld evidence."""
import base64, json, sys
from pathlib import Path
from collections import Counter
from osworld_openrouter_free import FREE_ROUTE
from osworld_groq_free import GROQ_FREE_ROUTE
from osworld_local_vlm import LOCAL_VLM_ROUTE
from osworld_local_text_review import review as local_text_review

SYSTEM = """You are a senior incident reviewer. Analyze only supplied evidence.
Return one compact JSON object with keys: root_cause_class, causal_chain,
recommended_fix, regression_risk, confidence, critical_dissent.
root_cause_class must be one of AGENT_LOGIC, PROVIDER_CAPACITY, INFRASTRUCTURE,
EVALUATOR, EVIDENCE_PROVENANCE, UNKNOWN. confidence is 0..1.
Never invent missing evidence. critical_dissent is true if a safe decision
cannot be made from the evidence."""

def load_evidence(root: Path):
    markers=("TERMINAL_FAIL","TASK_DEADLINE","PROVIDER","CAPACITY","WAIT_",
             "LOCAL_ACTION_UNAVAILABLE","ACTION_ISSUED","score","provenance",
             "AGENT_OUTPUT","FREE_","rate","429","403","quality","accessibility","HTTP 500","NoneType","Sample Colorize","Apply","EXPORT_PROVEN","Traceback")
    rows=[]
    names=('run.log','probe-result.json','task-rc.txt','osworld.log','shim.jsonl','gate-result.json','official-score.json')
    for name in names:
        for p in sorted(root.rglob(name)):
            if not p.is_file(): continue
            text=p.read_text(errors='replace')
            lines=text.splitlines()
            selected=[line for line in lines if any(m.casefold() in line.casefold() for m in markers)]
            if not selected: selected=lines[-30:]
            rows.append('### '+str(p.relative_to(root))+'\n'+'\n'.join(selected[-60:]))
    digest='\n\n'.join(rows)
    # 6k chars is intentionally below the smallest reviewer context after prompt/image overhead.
    return digest[-6000:]

def evidence_image(root: Path):
    candidates=[]
    for ext in ("*.png","*.jpg","*.jpeg","*.webp"):
        candidates.extend(root.rglob(ext))
    candidates=[p for p in candidates if p.is_file() and p.stat().st_size>0]
    if not candidates:return None
    p=max(candidates,key=lambda x:x.stat().st_mtime)
    mime="image/png" if p.suffix.lower()==".png" else "image/jpeg"
    return "data:%s;base64,%s"%(mime,base64.b64encode(p.read_bytes()).decode())

def parse_json(text):
    text=str(text or '').strip()
    a=text.find('{'); b=text.rfind('}')
    if a<0 or b<a: return None
    try:return json.loads(text[a:b+1])
    except json.JSONDecodeError:return None

NEUTRAL_IMAGE='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='

def ask(route, messages, budget):
    result, attempts=route.call({},budget=budget,raw_messages=messages,raw_tokens=900)
    parsed=parse_json((result or {}).get('text')) if result else None
    return {'verdict':parsed,'attempts':attempts,'raw':(result or {}).get('text','')}

def main(root: Path, codex_path=None):
    evidence=load_evidence(root)
    if not evidence: raise RuntimeError('INCIDENT_EVIDENCE_REQUIRED')
    text_messages=[{'role':'system','content':SYSTEM},{'role':'user','content':'INCIDENT EVIDENCE\n'+evidence}]
    vlm_messages=[{'role':'system','content':SYSTEM},{'role':'user','content':[
        {'type':'text','text':'INCIDENT EVIDENCE\n'+evidence},
        {'type':'image_url','image_url':{'url':NEUTRAL_IMAGE}}]}]
    reviews={
        'qwen_local':local_text_review('qwen_local',SYSTEM,evidence),
        'smollm_local':local_text_review('smollm_local',SYSTEM,evidence),
        'vlm_local':ask(LOCAL_VLM_ROUTE,vlm_messages,180),
        'groq_free':ask(GROQ_FREE_ROUTE,text_messages,100),
        'openrouter_free':ask(FREE_ROUTE,text_messages,100),
    }
    codex=None
    if codex_path:
        p=Path(codex_path)
        if not p.is_file(): raise RuntimeError('CODEX_REVIEW_REQUIRED_BUT_MISSING')
        codex=json.loads(p.read_text())
        reviews['codex']= {'verdict':codex,'attempts':[],'raw':''}
    valid={k:v['verdict'] for k,v in reviews.items() if isinstance(v.get('verdict'),dict)}
    classes=Counter(v.get('root_cause_class') for v in valid.values())
    top,count=classes.most_common(1)[0] if classes else ('UNKNOWN',0)
    critical=any(bool(v.get('critical_dissent')) for v in valid.values())
    quorum_required=4 if codex_path else 3
    converged=count>=4 if codex_path else count>=3
    accepted=len(valid)>=quorum_required and converged and not critical and top!='UNKNOWN'
    out={'status':'CONSENSUS_ACCEPTED' if accepted else 'CONSENSUS_BLOCKED',
         'root_cause_class':top,'votes':dict(classes),'reviews':reviews,
         'quorum_required':quorum_required,'valid_reviews':len(valid),
         'codex_required':bool(codex_path),'critical_dissent':critical}
    Path('osworld-v32-incident-consensus.json').write_text(json.dumps(out,indent=2))
    print(json.dumps({k:out[k] for k in ('status','root_cause_class','votes','valid_reviews','quorum_required','codex_required')}))
    if not accepted: raise RuntimeError('MULTI_AI_CONSENSUS_NOT_REACHED')

if __name__=='__main__':
    root=Path(sys.argv[1]); codex=sys.argv[2] if len(sys.argv)>2 else None
    main(root,codex)
