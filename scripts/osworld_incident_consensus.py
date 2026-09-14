"""Fail-closed multi-AI incident consensus for OSWorld evidence."""
import base64, json, sys
from pathlib import Path
from collections import Counter
from osworld_openrouter_free import FREE_ROUTE
from osworld_groq_free import GROQ_FREE_ROUTE
from osworld_local_vlm import LOCAL_VLM_ROUTE

SYSTEM = """You are a senior incident reviewer. Analyze only supplied evidence.
Return one compact JSON object with keys: root_cause_class, causal_chain,
recommended_fix, regression_risk, confidence, critical_dissent.
root_cause_class must be one of AGENT_LOGIC, PROVIDER_CAPACITY, INFRASTRUCTURE,
EVALUATOR, EVIDENCE_PROVENANCE, UNKNOWN. confidence is 0..1.
Never invent missing evidence. critical_dissent is true if a safe decision
cannot be made from the evidence."""

def load_evidence(root: Path):
    parts=[]
    for name in ('task-rc.txt','osworld.log','shim.jsonl','gate-result.json','official-score.json'):
        p=root/name
        if p.is_file():
            text=p.read_text(errors='replace')
            parts.append(f'### {name}\n{text[-18000:]}')
    return '\n\n'.join(parts)[-48000:]

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

def ask(route, messages, budget):
    result, attempts=route.call({},budget=budget,raw_messages=messages,raw_tokens=900)
    parsed=parse_json((result or {}).get('text')) if result else None
    return {'verdict':parsed,'attempts':attempts,'raw':(result or {}).get('text','')}

def main(root: Path, codex_path=None):
    evidence=load_evidence(root)
    if not evidence: raise RuntimeError('INCIDENT_EVIDENCE_REQUIRED')
    image=evidence_image(root)
    content=[{'type':'text','text':'INCIDENT EVIDENCE\n'+evidence}]
    if image:content.append({'type':'image_url','image_url':{'url':image}})
    messages=[{'role':'system','content':SYSTEM},{'role':'user','content':content}]
    reviews={
        'groq_free':ask(GROQ_FREE_ROUTE,messages,100),
        'openrouter_free':ask(FREE_ROUTE,messages,100),
        'local_cloud':ask(LOCAL_VLM_ROUTE,messages,180),
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
    converged=count>=3 if codex_path else count>=2
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
