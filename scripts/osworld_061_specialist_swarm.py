"""Ten-role FREE specialist swarm for OSWorld task 061 evidence."""
import json, sys
from pathlib import Path
from collections import Counter
from osworld_incident_consensus import load_evidence, evidence_image, ask
from osworld_openrouter_free import FREE_ROUTE
from osworld_groq_free import GROQ_FREE_ROUTE
from osworld_local_vlm import LOCAL_VLM_ROUTE
from osworld_local_text_review import review as local_text_review

ROLES = [
 ('gimp_gegl_color','GIMP/GEGL color-transfer specialist: inspect Sample Colorize sequencing, control states, processing completion and color fidelity.'),
 ('gtk_accessibility','GTK accessibility specialist: inspect a11y grounding, active-dialog scoping, stale geometry and accelerator fallbacks.'),
 ('osworld_executor','OSWorld execution specialist: inspect task state transitions, VM behavior, fixed-subset execution and termination semantics.'),
 ('official_evaluator','OSWorld evaluator specialist: explain the numeric 0.0 using only evidence; do not modify or weaken evaluator criteria.'),
 ('output_provenance','Forensic provenance specialist: verify that the agent itself creates ~/Pictures/IMG_7318_edited.jpg before any evaluator fallback.'),
 ('image_quality','Image-similarity specialist: inspect MSE/quality evidence and whether the produced image plausibly matches the reference grading.'),
 ('state_machine','Transaction/state-machine specialist: find phase jumps, ownership loss, false progress and action-issued-vs-state-verified errors.'),
 ('recovery_timing','GUI recovery/timing specialist: inspect asynchronous processing, Cancel/Close timing, bounded waits and settling conditions.'),
 ('zero_spend_mesh','ZERO_SPEND/provider specialist: verify no paid fallback, provider failures are not mistaken for agent-logic failures, heavy local remains zero.'),
 ('adversarial_qa','Adversarial QA specialist: try to falsify the champion fix and identify regressions, missing tests or unsupported assumptions.'),
]
BASE_SYSTEM = """You are one specialist reviewer in a fail-closed OSWorld task-061 audit.
Analyze only supplied evidence and the current champion contract. Return one compact JSON object with:
role, verdict, root_cause_class, causal_chain, definitive_fix, regression_risks, required_proofs,
confidence, veto. root_cause_class must be one of AGENT_LOGIC, EVIDENCE_PROVENANCE,
IMAGE_QUALITY, GUI_STATE, EVALUATOR, INFRASTRUCTURE, PROVIDER_CAPACITY, UNKNOWN.
verdict is PASS_FIX, REJECT_FIX, or INSUFFICIENT. veto=true if the current fix must not reach an official focal.
Never invent evidence, never weaken the official evaluator, and never propose paid fallback."""

def role_prompt(name, brief, evidence, champion):
    return BASE_SYSTEM + f"\nROLE={name}\nSPECIALTY={brief}\nCURRENT CHAMPION CONTRACT:\n{champion}\nINCIDENT EVIDENCE:\n{evidence}"

def parse_json(text):
    text=str(text or '').strip(); a=text.find('{'); b=text.rfind('}')
    if a<0 or b<a: return None
    try: return json.loads(text[a:b+1])
    except json.JSONDecodeError: return None
def run_robot(index, name, brief, evidence, champion):
    system=role_prompt(name,brief,evidence,champion)
    provider=index % 5
    if provider==0:
        result=local_text_review('qwen_local', system, evidence, max_new_tokens=420)
    elif provider==1:
        result=local_text_review('smollm_local', system, evidence, max_new_tokens=420)
    elif provider==2:
        msgs=[{'role':'system','content':system},{'role':'user','content':evidence}]
        result=ask(GROQ_FREE_ROUTE,msgs,120)
    elif provider==3:
        msgs=[{'role':'system','content':system},{'role':'user','content':evidence}]
        result=ask(FREE_ROUTE,msgs,120)
    else:
        msgs=[{'role':'system','content':system},{'role':'user','content':[
            {'type':'text','text':evidence},
            {'type':'image_url','image_url':{'url':'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='}}]}]
        result=ask(LOCAL_VLM_ROUTE,msgs,180)
    verdict=result.get('verdict') if isinstance(result,dict) else None
    return {'role':name,'specialty':brief,'provider_slot':provider,'result':result,'verdict':verdict}
def main(root: Path):
    evidence=load_evidence(root)
    if not evidence: raise RuntimeError('INCIDENT_EVIDENCE_REQUIRED')
    champion_path=Path('scripts/osworld_061_champion.py')
    style_path=Path('scripts/osworld_gimp_style_transfer.py')
    if not champion_path.is_file() or not style_path.is_file():
        raise RuntimeError('CHAMPION_CODE_REQUIRED')
    calibrated=Path('scripts/osworld_061_calibrated_grade.py')
    shim=Path('scripts/osworld_free_mesh_shim.py')
    if not calibrated.is_file() or not shim.is_file(): raise RuntimeError('CALIBRATED_CHAMPION_REQUIRED')
    champion=(champion_path.read_text(errors='replace')+'\n\n'+style_path.read_text(errors='replace')+'\n\n'+calibrated.read_text(errors='replace')+'\n\n'+shim.read_text(errors='replace'))[-18000:]
    robots=[run_robot(i,name,brief,evidence,champion) for i,(name,brief) in enumerate(ROLES)]
    valid=[r for r in robots if isinstance(r.get('verdict'),dict)]
    vetoes=[r['role'] for r in valid if bool(r['verdict'].get('veto')) or r['verdict'].get('verdict')!='PASS_FIX']
    classes=Counter(str(r['verdict'].get('root_cause_class') or 'UNKNOWN') for r in valid)
    required={'gimp_gegl_color','gtk_accessibility','osworld_executor','official_evaluator','output_provenance',
              'image_quality','state_machine','recovery_timing','zero_spend_mesh','adversarial_qa'}
    covered={r['role'] for r in valid}
    accepted=(len(valid)==10 and covered==required and not vetoes and classes.get('UNKNOWN',0)==0)
    out={'status':'SWARM_ACCEPTED' if accepted else 'SWARM_BLOCKED','robots_total':10,
         'valid_reviews':len(valid),'covered_roles':sorted(covered),'root_cause_votes':dict(classes),
         'vetoes':vetoes,'reviews':robots,'zero_spend_mode':'HARD','paid_fallback_used':False,'heavy_local':0}
    Path('osworld-061-specialist-swarm.json').write_text(json.dumps(out,indent=2))
    print(json.dumps({k:out[k] for k in ('status','robots_total','valid_reviews','root_cause_votes','vetoes')}))
    if not accepted: raise RuntimeError('SPECIALIST_SWARM_BLOCKED')

if __name__=='__main__':
    main(Path(sys.argv[1]))
