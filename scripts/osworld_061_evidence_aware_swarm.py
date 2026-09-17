"""Bind validated official focal proof into the existing fail-closed 061 swarm."""
import json, os, sys
from pathlib import Path
import osworld_061_specialist_swarm as s
OFFICIAL=''
def load_official(root):
    if os.environ.get('APPROVED_FOCAL_EVIDENCE_BOUND')!='1': raise RuntimeError('APPROVED_FOCAL_EVIDENCE_NOT_BOUND')
    sha=os.environ.get('APPROVED_FOCAL_SHA'); run=os.environ.get('APPROVED_FOCAL_RUN_ID')
    c=list(root.rglob('candidate-sha.txt')); r=list(root.rglob('results.json'))
    rc=list(root.rglob('task-rc.txt')); z=list(root.rglob('zero-spend-mode.txt'))
    if not sha or not run or not all(len(x)==1 for x in (c,r,rc,z)): raise RuntimeError('APPROVED_FOCAL_EVIDENCE_INCOMPLETE')
    rows=[x for x in json.loads(r[0].read_text()) if x.get('task_id')=='061']
    if c[0].read_text().strip()!=sha or rc[0].read_text().strip()!='0' or z[0].read_text().strip()!='HARD': raise RuntimeError('APPROVED_FOCAL_EVIDENCE_INVALID')
    if len(rows)!=1 or rows[0].get('status')!='success' or rows[0].get('score')!=1.0: raise RuntimeError('APPROVED_FOCAL_061_NOT_PERFECT')
    return json.dumps({'source_run_id':run,'approved_focal_sha':sha,'status':'FOCAL_061_PASS','official_score':1.0,'task_rc':0,'evaluator':'OSWorld V2 official','zero_spend_mode':'HARD','heavy_local':0},separators=(',',':'))
def comb(old,probe):
    return 'APPROVED OFFICIAL FOCAL EVIDENCE (validated):\n'+OFFICIAL+'\nCURRENT PARITY-BOUND DIAGNOSTIC EVIDENCE:\n'+probe+'\nHISTORICAL FAILED-SHA EVIDENCE (context only):\n'+old
def txt(system,evidence,probe=''): return [{'role':'system','content':system},{'role':'user','content':comb(evidence,probe)}]
def vlm(system,evidence,image,probe=''): return [{'role':'system','content':system},{'role':'user','content':[{'type':'text','text':comb(evidence,probe)},{'type':'image_url','image_url':{'url':image}}]}]
def loc(evidence,probe=''): return comb(evidence,probe)
def binary(name,brief,evidence,contract,image,probe=''):
    # A one-token VLM YES/NO is not an authoritative specialist verdict.  The
    # structured reviewers below must identify a concrete causal gap if they veto.
    return None,[]
def main(root):
    global OFFICIAL; root=Path(root); OFFICIAL=load_official(root)
    s.BASE_SYSTEM=s.BASE_SYSTEM.replace('This is a pre-focal source audit: runtime proof belongs in required_proofs;\nabsence of runtime proof alone is not a source-level veto.','This is a post-focal audit. Validated approved official focal evidence is supplied. Do not request proof already present there; veto only for a concrete remaining causal gap or regression. A REJECT_FIX verdict must name that concrete gap in causal_chain; otherwise return PASS_FIX or INSUFFICIENT without veto.')
    s._text_messages=txt; s._vlm_messages=vlm; s._local_evidence=loc; s._local_binary_review=binary
    s.main(root)
if __name__=='__main__': main(sys.argv[1])
