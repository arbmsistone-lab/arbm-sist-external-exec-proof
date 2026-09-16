"""Ten-role FREE specialist audit for the historical OSWorld task-061 incident.

The audit compares historical failure evidence with compact source excerpts from
the current candidate. It is advisory evidence and never changes the official
evaluator or score gate.
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path
from osworld_incident_consensus import load_evidence, evidence_image, ask
from osworld_openrouter_free import FREE_ROUTE
from osworld_groq_free import GROQ_FREE_ROUTE
from osworld_local_vlm import LOCAL_VLM_ROUTE
from osworld_local_text_review import review as local_text_review

ROLES = [
 ('gimp_gegl_color','GIMP/GEGL color-transfer sequencing and color fidelity.'),
 ('gtk_accessibility','GTK accessibility grounding, dialog scope and accelerators.'),
 ('osworld_executor','OSWorld state transitions, VM execution and termination.'),
 ('official_evaluator','Evaluator interpretation without changing evaluator criteria.'),
 ('output_provenance','Agent-created output provenance before evaluator fallback.'),
 ('image_quality','Reference-transfer quality evidence and validation.'),
 ('state_machine','Ownership, phase acknowledgements and false-progress handling.'),
 ('recovery_timing','Asynchronous processing, bounded waits and settling.'),
 ('zero_spend_mesh','ZERO_SPEND provider behavior and failure classification.'),
 ('adversarial_qa','Adversarial regression review of the current candidate.'),
]
ROOT_CLASSES={'AGENT_LOGIC','EVIDENCE_PROVENANCE','IMAGE_QUALITY','GUI_STATE','EVALUATOR','INFRASTRUCTURE','PROVIDER_CAPACITY','UNKNOWN'}
VERDICTS={'PASS_FIX','REJECT_FIX','INSUFFICIENT'}
BASE_SYSTEM="""You are one specialist reviewer in a fail-closed OSWorld task-061 audit.
The INCIDENT EVIDENCE is historical and describes a failed older SHA. The
CURRENT CANDIDATE CONTRACT is newer source code intended to fix that incident.
Do not veto merely because the historical incident failed. Veto only when the
current source excerpts still leave a specific causal gap or regression.
Return exactly one compact JSON object with keys: role, verdict,
root_cause_class, causal_chain, definitive_fix, regression_risks,
required_proofs, confidence, veto. verdict is PASS_FIX, REJECT_FIX, or
INSUFFICIENT. confidence must be numeric 0..1 and veto must be boolean.
Never invent evidence, never weaken the official evaluator, and never propose
paid fallback."""

def _function_source(path, name, limit):
    text=Path(path).read_text(encoding='utf-8',errors='replace')
    token='def '+name+'('
    start=text.find(token)
    if start < 0: return ''
    tail=text[start:]
    cuts=[p for p in (tail.find('\ndef ',1),tail.find('\nclass ',1)) if p>0]
    end=min(cuts) if cuts else len(tail)
    return tail[:end][:limit]

def current_contract():
    parts=[
      _function_source('scripts/osworld_061_calibrated_grade.py','next_calibrated_action',1800),
      _function_source('scripts/osworld_free_mesh_shim.py','try_061_calibrated',1500),
      _function_source('scripts/osworld_free_mesh_shim.py','_ack_gimp_pending',1500),
      _function_source('scripts/osworld_free_mesh_shim.py','try_gimp_specialist',1800),
    ]
    return '\n\n'.join(x for x in parts if x)[:6000]

def role_prompt(name, brief, contract):
    return (BASE_SYSTEM+f'\nROLE={name}\nSPECIALTY={brief}\n'
            +'CURRENT CANDIDATE CONTRACT (source excerpts):\n'+contract)

def parse_json(text):
    text=str(text or '').strip(); a=text.find('{'); b=text.rfind('}')
    if a<0 or b<a: return None
    try: return json.loads(text[a:b+1])
    except json.JSONDecodeError: return None

def valid_verdict(value, role):
    if not isinstance(value,dict) or value.get('role')!=role: return False
    if value.get('verdict') not in VERDICTS: return False
    if value.get('root_cause_class') not in ROOT_CLASSES: return False
    if not isinstance(value.get('causal_chain'),list): return False
    if not isinstance(value.get('regression_risks'),list): return False
    if not isinstance(value.get('required_proofs'),list): return False
    if type(value.get('veto')) is not bool: return False
    confidence=value.get('confidence')
    return isinstance(confidence,(int,float)) and not isinstance(confidence,bool) and 0<=confidence<=1

def _text_messages(system,evidence):
    user=('HISTORICAL INCIDENT EVIDENCE. Decide whether the CURRENT candidate '
          'source excerpts resolve your specialty-specific causal gap.\n'+evidence)
    return [{'role':'system','content':system},{'role':'user','content':user}]

def _vlm_messages(system,evidence,image):
    return [{'role':'system','content':system},{'role':'user','content':[
        {'type':'text','text':'HISTORICAL INCIDENT EVIDENCE\n'+evidence},
        {'type':'image_url','image_url':{'url':image}}]}]

def run_robot(index, name, brief, evidence, contract, image):
    system=role_prompt(name,brief,contract)
    attempts=[]; raw_outputs=[]
    for label in ('openrouter','groq','qwen_local','smollm_local','local_vlm'):
        if label=='openrouter': result=ask(FREE_ROUTE,_text_messages(system,evidence),140)
        elif label=='groq': result=ask(GROQ_FREE_ROUTE,_text_messages(system,evidence),120)
        elif label=='qwen_local': result=local_text_review('qwen_local',system,evidence,max_new_tokens=320)
        elif label=='smollm_local': result=local_text_review('smollm_local',system,evidence,max_new_tokens=320)
        else:
            if not image: continue
            result=ask(LOCAL_VLM_ROUTE,_vlm_messages(system,evidence,image),180)
        attempts.extend(result.get('attempts') or [])
        raw_outputs.append({'provider':label,'raw':str(result.get('raw') or '')[-1200:]})
        verdict=result.get('verdict')
        if valid_verdict(verdict,name):
            return {'role':name,'specialty':brief,'provider':label,
                    'verdict':verdict,'attempts':attempts,'raw_outputs':raw_outputs}
    return {'role':name,'specialty':brief,'provider':None,'verdict':None,
            'attempts':attempts,'raw_outputs':raw_outputs}

def main(root: Path):
    evidence=load_evidence(root)
    if not evidence: raise RuntimeError('INCIDENT_EVIDENCE_REQUIRED')
    contract=current_contract()
    if not contract: raise RuntimeError('CURRENT_CANDIDATE_CONTRACT_REQUIRED')
    image=evidence_image(root)
    robots=[run_robot(i,name,brief,evidence,contract,image)
            for i,(name,brief) in enumerate(ROLES)]
    valid=[r for r in robots if valid_verdict(r.get('verdict'),r['role'])]
    vetoes=[r['role'] for r in valid if r['verdict']['veto'] or r['verdict']['verdict']!='PASS_FIX']
    classes=Counter(r['verdict']['root_cause_class'] for r in valid)
    required={name for name,_ in ROLES}; covered={r['role'] for r in valid}
    accepted=(len(valid)==10 and covered==required and not vetoes and classes.get('UNKNOWN',0)==0)
    out={'status':'SWARM_ACCEPTED' if accepted else 'SWARM_BLOCKED',
         'candidate_sha':os.environ.get('GITHUB_SHA'),'historical_evidence':True,
         'robots_total':10,'valid_reviews':len(valid),'covered_roles':sorted(covered),
         'root_cause_votes':dict(classes),'vetoes':vetoes,'reviews':robots,
         'zero_spend_mode':'HARD','paid_fallback_used':False,'heavy_local':0}
    Path('osworld-061-specialist-swarm.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps({k:out[k] for k in ('status','candidate_sha','robots_total','valid_reviews','root_cause_votes','vetoes')}))
    if not accepted: raise RuntimeError('SPECIALIST_SWARM_BLOCKED')

if __name__=='__main__':
    main(Path(sys.argv[1]))
