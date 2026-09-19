"""Ten-role FREE specialist audit for the historical OSWorld task-061 incident.

The audit compares historical failure evidence with compact source excerpts from
the current candidate. It is advisory evidence and never changes the official
evaluator or score gate.
"""
import json
import hashlib
import os
import sys
from collections import Counter
from pathlib import Path
from osworld_incident_consensus import load_evidence, evidence_image, ask
from osworld_openrouter_free import FREE_ROUTE
from osworld_groq_free import GROQ_FREE_ROUTE
from osworld_local_vlm import LOCAL_VLM_ROUTE
from osworld_local_text_review import review as local_text_review, clear_runtime_cache as clear_local_text_cache

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
This is a pre-focal source audit: runtime proof belongs in required_proofs;
absence of runtime proof alone is not a source-level veto.
Return exactly one compact JSON object with keys: role, verdict,
root_cause_class, causal_chain, definitive_fix, regression_risks,
required_proofs, confidence, veto. verdict is PASS_FIX, REJECT_FIX, or
INSUFFICIENT. confidence must be numeric 0..1 and veto must be boolean.
Never invent evidence, never weaken the official evaluator, and never propose
paid fallback.
STRICT SCHEMA: role must exactly equal the assigned ROLE. root_cause_class must be exactly one of AGENT_LOGIC, EVIDENCE_PROVENANCE, IMAGE_QUALITY, GUI_STATE, EVALUATOR, INFRASTRUCTURE, PROVIDER_CAPACITY, UNKNOWN. causal_chain, regression_risks, and required_proofs must always be JSON arrays, even for one item. Do not use prose labels or synonyms for enum fields."""

def _function_source(path, name, limit):
    text=Path(path).read_text(encoding='utf-8',errors='replace')
    token='def '+name+'('
    start=text.find(token)
    if start < 0: return ''
    tail=text[start:]
    cuts=[p for p in (tail.find('\ndef ',1),tail.find('\nclass ',1)) if p>0]
    end=min(cuts) if cuts else len(tail)
    return tail[:end][:limit]

def _source_window(path, needle, before=700, after=1000):
    text=Path(path).read_text(encoding='utf-8',errors='replace')
    pos=text.find(needle)
    if pos<0: return ''
    return text[max(0,pos-before):min(len(text),pos+len(needle)+after)]

def current_contract():
    parts=[
      _source_window('scripts/osworld_061_calibrated_grade.py','print(f"ARBM061_DONE',300,240),
      _source_window('scripts/osworld_061_calibrated_grade.py','def next_calibrated_action',0,1300),
      _source_window('scripts/osworld_free_mesh_shim.py','def try_061_calibrated',0,1300),
      _source_window('scripts/osworld_free_mesh_shim.py','calibrated_result=try_061_calibrated',180,420),
      _source_window('scripts/osworld_free_mesh_shim.py','def _ack_gimp_pending',0,1080),
      _source_window('scripts/osworld_free_mesh_shim.py','specialist_complete=',900,550),
      _source_window('scripts/osworld_gimp_style_transfer.py','def next_recovery_action',0,260),
      _source_window('scripts/osworld_gimp_style_transfer.py','The official 061 VM exposes a bottom Cancel button',420,800),
      _source_window('scripts/osworld_gimp_style_transfer.py','ARBM061_GIMP_EXPORT_PROVENANCE_SUCCESS',350,750),
      _source_window('scripts/osworld_gimp_style_transfer.py','Export Image as JPEG / Export',80,220),
    ]
    contract='\n\n'.join(x for x in parts if x)
    if len(contract)>9500:
        raise RuntimeError('CURRENT_CONTRACT_TOO_LARGE')
    return contract

def load_probe_evidence(root):
    root=Path(root)
    cal_path=root/'calibrated'/'calibrated-probe-result.json'
    gimp_path=root/'gimp'/'probe-result.json'
    absent_path=root/'gimp'/'output-absent-before-export.txt'
    if not (cal_path.is_file() and gimp_path.is_file() and absent_path.is_file()):
        return ''
    cal=json.loads(cal_path.read_text(encoding='utf-8'))
    gimp=json.loads(gimp_path.read_text(encoding='utf-8'))
    if os.environ.get('DIAGNOSTIC_EXECUTION_PARITY')!='1':
        return ''
    if cal.get('status')!='CALIBRATED_EXPORT_PROVEN' or gimp.get('status')!='EXPORT_PROVEN':
        return ''
    if cal.get('output')!='IMG_7318_edited.jpg' or gimp.get('output')!='IMG_7318_edited.jpg':
        return ''
    expected=os.environ.get('DIAGNOSTIC_PROBE_SHA')
    run_id=os.environ.get('DIAGNOSTIC_PROBE_RUN_ID')
    if not expected or not run_id:
        return ''
    if cal.get('candidate_sha')!=expected or gimp.get('candidate_sha')!=expected:
        return ''
    if cal.get('zero_spend_mode')!='HARD' or gimp.get('zero_spend_mode')!='HARD':
        return ''
    if cal.get('heavy_local')!=0 or gimp.get('heavy_local')!=0:
        return ''
    rmse=cal.get('reference_rmse'); cal_bytes=cal.get('output_bytes'); gimp_bytes=gimp.get('output_bytes')
    cal_sha=cal.get('output_sha256'); gimp_sha=gimp.get('output_sha256')
    if not isinstance(rmse,(int,float)) or isinstance(rmse,bool): return ''
    if not isinstance(cal_bytes,int) or cal_bytes<=1024 or not isinstance(gimp_bytes,int) or gimp_bytes<=1024: return ''
    if not (isinstance(cal_sha,str) and len(cal_sha)==64 and isinstance(gimp_sha,str) and len(gimp_sha)==64): return ''
    if gimp.get('output_visible_in_chooser') is not True: return ''
    if absent_path.read_text(encoding='utf-8').strip()!='/home/user/Pictures/IMG_7318_edited.jpg': return ''
    cal_output=root/'calibrated'/cal['output']; gimp_output=root/'gimp'/gimp['output']
    if not cal_output.is_file() or not gimp_output.is_file(): return ''
    if cal_output.stat().st_size!=cal_bytes or gimp_output.stat().st_size!=gimp_bytes: return ''
    def digest(path):
        h=hashlib.sha256()
        with path.open('rb') as fh:
            for chunk in iter(lambda:fh.read(1024*1024),b''): h.update(chunk)
        return h.hexdigest()
    if digest(cal_output)!=cal_sha or digest(gimp_output)!=gimp_sha: return ''
    stages=('43-sample-colorize-dialog.png','46-subcolors-enabled.png',
      '47-hold-intensity-disabled.png','48-original-intensity-disabled.png',
      '50-sample-colors-loaded.png','60-colorize-applied.png','70-colorize-closed.png',
      '80-export-open-00.png','81-export-name.png','82-export-state-00.png',
      '90-output-chooser.png','91-output-pictures.png')
    if any(not (root/'gimp'/name).is_file() or (root/'gimp'/name).stat().st_size<=0 for name in stages): return ''
    summary={
      'purpose':'CURRENT DIAGNOSTIC PROBE EVIDENCE; diagnostic only, no evaluator/score',
      'source_run_id':run_id,
      'execution_parity_verified':True,
      'calibrated':{'candidate_sha':cal.get('candidate_sha'),'status':cal.get('status'),
        'reference_rmse':rmse,'model':cal.get('model'),'output':cal.get('output'),'output_bytes':cal_bytes,'output_sha256':cal_sha,'zero_spend_mode':cal.get('zero_spend_mode'),'heavy_local':cal.get('heavy_local')},
      'gimp_ui':{'candidate_sha':gimp.get('candidate_sha'),'status':gimp.get('status'),
        'output':gimp.get('output'),'output_visible_in_chooser':gimp.get('output_visible_in_chooser'),
        'output_bytes':gimp.get('output_bytes'),'output_sha256':gimp.get('output_sha256'),
        'output_absent_before_export':True,'zero_spend_mode':gimp.get('zero_spend_mode'),'heavy_local':gimp.get('heavy_local'),'stage_snapshots_present':[name for name in stages]},
      'scope_note':'Probe supports runtime route/evidence only; official focal evaluator score remains required.'}
    return json.dumps(summary,separators=(',',':'))

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

def canonicalize_shape(value):
    if not isinstance(value,dict): return value
    out=dict(value)
    for key in ('causal_chain','regression_risks','required_proofs'):
        if isinstance(out.get(key),str): out[key]=[out[key]]
        elif out.get(key) is None: out[key]=[]
    return out

def _repair_messages(name, raw):
    prompt=(f'Re-emit the SAME substantive judgment as strict JSON. role must be exactly {name}. '
            'verdict must be PASS_FIX, REJECT_FIX, or INSUFFICIENT. root_cause_class must be exactly one of '
            'AGENT_LOGIC, EVIDENCE_PROVENANCE, IMAGE_QUALITY, GUI_STATE, EVALUATOR, INFRASTRUCTURE, '
            'PROVIDER_CAPACITY, UNKNOWN. causal_chain, regression_risks, required_proofs must be arrays. '
            'confidence 0..1; veto boolean. Preserve the original conclusion and veto meaning; do not add evidence.\nORIGINAL REVIEW:\n'+str(raw)[-2200:])
    return [{'role':'system','content':'You are a schema repairer. Change format only, never substance.'},
            {'role':'user','content':prompt}]

def _text_messages(system,evidence,probe_evidence=''):
    user=('HISTORICAL INCIDENT EVIDENCE. Decide whether the CURRENT candidate '
          'source excerpts resolve your specialty-specific causal gap.\n'+evidence)
    if probe_evidence:
        user += ('\n\nCURRENT DIAGNOSTIC PROBE EVIDENCE (non-official; no evaluator/score; execution parity verified):\n'+probe_evidence)
    return [{'role':'system','content':system},{'role':'user','content':user}]

def _vlm_messages(system,evidence,image,probe_evidence=''):
    text='HISTORICAL INCIDENT EVIDENCE\n'+evidence
    if probe_evidence:
        text += ('\n\nCURRENT DIAGNOSTIC PROBE EVIDENCE (non-official; no evaluator/score; execution parity verified):\n'+probe_evidence)
    return [{'role':'system','content':system},{'role':'user','content':[
        {'type':'text','text':text},{'type':'image_url','image_url':{'url':image}}]}]

def _local_evidence(evidence, probe_evidence=''):
    if not probe_evidence:
        return evidence
    return ('CURRENT DIAGNOSTIC PROBE EVIDENCE (non-official; no evaluator/score; '
            'execution parity verified):\n'+probe_evidence+
            '\n\nHISTORICAL INCIDENT EVIDENCE:\n'+evidence)

def _local_binary_review(name, brief, evidence, contract, image, probe_evidence=''):
    if not image: return None,[]
    question=(f'ROLE={name}. SPECIALTY={brief}. Decide only from supplied evidence whether the CURRENT candidate '
      'resolves the historical causal gap for this specialty without weakening evaluator, provenance, ZERO_SPEND, '
      'or fail-closed behavior. Answer exactly YES OR NO. YES only if the source contract and current diagnostic '
      'probe evidence jointly support closure for this role; otherwise NO.\nCURRENT CONTRACT:\n'+contract+
      '\nCURRENT DIAGNOSTIC PROBE:\n'+probe_evidence+'\nHISTORICAL INCIDENT:\n'+evidence)
    messages=[{'role':'user','content':[{'type':'text','text':question},{'type':'image_url','image_url':{'url':image}}]}]
    result,attempts=LOCAL_VLM_ROUTE.call({},budget=180,raw_messages=messages,raw_tokens=8)
    raw=str((result or {}).get('text') or '').strip().upper()
    if raw not in ('YES','NO'): return None,attempts
    verdict={'role':name,'verdict':'PASS_FIX' if raw=='YES' else 'REJECT_FIX',
      'root_cause_class':'AGENT_LOGIC','causal_chain':['deterministic local binary review over current contract and approved diagnostic evidence'],
      'definitive_fix':'current candidate accepted for this role' if raw=='YES' else 'current evidence insufficient for this role',
      'regression_risks':[],'required_proofs':['official focal score 1.0','approved evidence manifest','world audit'],
      'confidence':0.8,'veto':raw!='YES'}
    return verdict,attempts

def run_robot(index, name, brief, evidence, contract, image, probe_evidence=''):
    system=role_prompt(name,brief,contract)
    attempts=[]; raw_outputs=[]
    compact_post_focal=os.environ.get('ARBM_POST_FOCAL_COMPACT_LOCAL')=='1'
    labels=('openrouter','groq','qwen_local') if compact_post_focal else ('openrouter','groq','qwen_local','smollm_local','local_vlm')
    for label in labels:
        if label=='openrouter': result=ask(FREE_ROUTE,_text_messages(system,evidence,probe_evidence),140)
        elif label=='groq': result=ask(GROQ_FREE_ROUTE,_text_messages(system,evidence,probe_evidence),120)
        elif label=='qwen_local':
            verdict,binary_attempts=_local_binary_review(name,brief,evidence,contract,image,probe_evidence)
            attempts.extend(binary_attempts)
            if valid_verdict(verdict,name):
                return {'role':name,'specialty':brief,'provider':'local_binary_vlm','verdict':verdict,'attempts':attempts,'raw_outputs':raw_outputs}
            result=local_text_review('qwen_local',system,_local_evidence(evidence,probe_evidence),max_new_tokens=160)
        elif label=='smollm_local': result=local_text_review('smollm_local',system,_local_evidence(evidence,probe_evidence),max_new_tokens=160)
        else:
            if not image: continue
            clear_local_text_cache()
            result=ask(LOCAL_VLM_ROUTE,_vlm_messages(system,evidence,image,probe_evidence),180)
        attempts.extend(result.get('attempts') or [])
        raw_outputs.append({'provider':label,'raw':str(result.get('raw') or '')[-1200:]})
        verdict=canonicalize_shape(result.get('verdict'))
        if valid_verdict(verdict,name):
            return {'role':name,'specialty':brief,'provider':label,
                    'verdict':verdict,'attempts':attempts,'raw_outputs':raw_outputs}
        raw=str(result.get('raw') or '')
        if raw and label in ('openrouter','groq'):
            repaired=ask(FREE_ROUTE if label=='openrouter' else GROQ_FREE_ROUTE,_repair_messages(name,raw),100)
            attempts.extend(repaired.get('attempts') or [])
            raw_outputs.append({'provider':label+'-schema-repair','raw':str(repaired.get('raw') or '')[-1200:]})
            verdict=canonicalize_shape(repaired.get('verdict'))
            if valid_verdict(verdict,name):
                return {'role':name,'specialty':brief,'provider':label+'-schema-repair',
                        'verdict':verdict,'attempts':attempts,'raw_outputs':raw_outputs}
    return {'role':name,'specialty':brief,'provider':None,'verdict':None,
            'attempts':attempts,'raw_outputs':raw_outputs}

def main(root: Path):
    evidence=load_evidence(root)
    if not evidence: raise RuntimeError('INCIDENT_EVIDENCE_REQUIRED')
    contract=current_contract()
    if not contract: raise RuntimeError('CURRENT_CANDIDATE_CONTRACT_REQUIRED')
    image=evidence_image(root)
    probe_evidence=load_probe_evidence(Path(os.environ.get('CURRENT_PROBE_EVIDENCE','current-probe-evidence')))
    if not probe_evidence: raise RuntimeError('CURRENT_DIAGNOSTIC_PROBE_EVIDENCE_REQUIRED')
    try:
        robots=[run_robot(i,name,brief,evidence,contract,image,probe_evidence)
                for i,(name,brief) in enumerate(ROLES)]
    finally:
        clear_local_text_cache()
    valid=[r for r in robots if valid_verdict(r.get('verdict'),r['role'])]
    vetoes=[r['role'] for r in valid if r['verdict']['veto'] or r['verdict']['verdict']!='PASS_FIX']
    classes=Counter(r['verdict']['root_cause_class'] for r in valid)
    required={name for name,_ in ROLES}; covered={r['role'] for r in valid}
    accepted=(len(valid)==10 and covered==required and not vetoes and classes.get('UNKNOWN',0)==0)
    out={'status':'SWARM_ACCEPTED' if accepted else 'SWARM_BLOCKED',
         'candidate_sha':os.environ.get('GITHUB_SHA'),'historical_evidence':True,
         'robots_total':10,'valid_reviews':len(valid),'covered_roles':sorted(covered),
         'root_cause_votes':dict(classes),'vetoes':vetoes,'reviews':robots,
         'diagnostic_probe':json.loads(probe_evidence),
         'zero_spend_mode':'HARD','paid_fallback_used':False,'heavy_local':0}
    Path('osworld-061-specialist-swarm.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print(json.dumps({k:out[k] for k in ('status','candidate_sha','robots_total','valid_reviews','root_cause_votes','vetoes')}))
    if not accepted: raise RuntimeError('SPECIALIST_SWARM_BLOCKED')

if __name__=='__main__':
    main(Path(sys.argv[1]))
