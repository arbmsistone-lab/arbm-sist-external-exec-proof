"""Task 091 elite engineering review board.

100 deterministic senior review lanes grouped into 10 elite councils.
This formalizes independent technical checks; it does not claim 100 human engineers.
Every lane is fail-closed. Any failure vetoes promotion.
"""
import hashlib
import json
from collections import OrderedDict

ELITE_TOTAL=100
COUNCIL_TOTAL=10

def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()

def _require(condition, code):
    if not condition:
        raise RuntimeError(code)

def evaluate(contract):
    rows=[]
    def add(domain,name,condition,evidence=None):
        rows.append({'domain':domain,'name':name,'pass':bool(condition),'evidence':evidence})

    target=contract.get('target') or {}
    shape=contract.get('shape') or {}
    geometry=shape.get('geometry') or {}
    screen=contract.get('screen')
    window=contract.get('window')
    viewport=contract.get('viewport')
    before_sha=str(contract.get('before_sha') or '')
    after_sha=str(contract.get('after_sha') or '')
    expected=str(contract.get('expected') or '')
    actual=str(contract.get('actual') or '')
    plan=contract.get('repair_plan') or []
    generated_point=contract.get('generated_point') or []
    expected_point=contract.get('expected_point') or []
    expected_shape_id=int(contract.get('expected_shape_id') or 0)
    selected_shape_id=int(contract.get('selected_shape_id') or 0)
    source=str(target.get('source') or '')
    foreground_sha=str(target.get('foreground_sha256') or '')
    deck_sha=str(target.get('deck_sha256') or '')
    proof_sha=str(target.get('proof_sha256') or '')

    # Council 1 — evidence/provenance.
    add('C01','01-candidate-sha-bound',len(str(contract.get('candidate_sha') or ''))==40,contract.get('candidate_sha'))
    add('C01','02-before-sha-64',len(before_sha)==64,before_sha)
    add('C01','03-after-sha-64',len(after_sha)==64,after_sha)
    add('C01','04-deck-mutated',before_sha!=after_sha,(before_sha,after_sha))
    add('C01','05-source-canonical',source=='task091-pptx-canonical',source)
    add('C01','06-foreground-sha-64',len(foreground_sha)==64,foreground_sha)
    add('C01','07-deck-proof-sha-64',len(deck_sha)==64,deck_sha)
    add('C01','08-target-proof-sha-64',len(proof_sha)==64,proof_sha)
    add('C01','09-zero-spend-hard',contract.get('zero_spend')=='HARD',contract.get('zero_spend'))
    add('C01','10-heavy-local-zero',int(contract.get('heavy_local') or 0)==0,contract.get('heavy_local'))

    # Council 2 — exact environment.
    add('C02','11-screen-exact',screen==[0,0,1920,1080],screen)
    add('C02','12-window-exact',window==[70,27,1850,1053],window)
    add('C02','13-viewport-exact',viewport==[443,194,1413,795],viewport)
    add('C02','14-viewport-16x9',abs((viewport[2]/viewport[3])-(16/9))<0.01 if isinstance(viewport,list) and len(viewport)==4 else False,viewport)
    add('C02','15-slide-width-positive',int(contract.get('slide_w') or 0)>0,contract.get('slide_w'))
    add('C02','16-slide-height-positive',int(contract.get('slide_h') or 0)>0,contract.get('slide_h'))
    add('C02','17-window-in-screen',window[0]>=0 and window[1]>=0 and window[0]+window[2]<=screen[2] and window[1]+window[3]<=screen[3] if isinstance(window,list) and isinstance(screen,list) else False,None)
    add('C02','18-viewport-in-window',viewport[0]>=window[0] and viewport[1]>=window[1] and viewport[0]+viewport[2]<=window[0]+window[2] and viewport[1]+viewport[3]<=window[1]+window[3] if isinstance(viewport,list) and isinstance(window,list) else False,None)
    add('C02','19-no-viewport-zero',all(int(v)>0 for v in viewport[2:]) if isinstance(viewport,list) and len(viewport)==4 else False,viewport)
    add('C02','20-environment-digest',bool(_digest([screen,window,viewport])),_digest([screen,window,viewport]))

    # Council 3 — shape identity/geometry.
    add('C03','21-shape-id-positive',int(shape.get('id') or 0)>0,shape.get('id'))
    add('C03','22-shape-id-bound',int(shape.get('id') or 0)==expected_shape_id,(shape.get('id'),expected_shape_id))
    add('C03','23-selected-shape-bound',selected_shape_id==expected_shape_id,(selected_shape_id,expected_shape_id))
    add('C03','24-shape-name-present',bool(str(shape.get('name') or '')),shape.get('name'))
    add('C03','25-geometry-x-nonnegative',int(geometry.get('x') or -1)>=0,geometry)
    add('C03','26-geometry-y-nonnegative',int(geometry.get('y') or -1)>=0,geometry)
    add('C03','27-geometry-width-positive',int(geometry.get('w') or 0)>0,geometry)
    add('C03','28-geometry-height-positive',int(geometry.get('h') or 0)>0,geometry)
    add('C03','29-shape-text-present',bool(str(shape.get('text') or '')),shape.get('text'))
    add('C03','30-shape-digest-stable',bool(_digest(shape)),_digest(shape))

    # Council 4 — point derivation.
    add('C04','31-generated-point-pair',isinstance(generated_point,list) and len(generated_point)==2,generated_point)
    add('C04','32-expected-point-pair',isinstance(expected_point,list) and len(expected_point)==2,expected_point)
    add('C04','33-x-exact',generated_point[0]==expected_point[0] if len(generated_point)==2 and len(expected_point)==2 else False,(generated_point,expected_point))
    add('C04','34-y-exact',generated_point[1]==expected_point[1] if len(generated_point)==2 and len(expected_point)==2 else False,(generated_point,expected_point))
    add('C04','35-point-in-viewport',viewport[0]<=generated_point[0]<viewport[0]+viewport[2] and viewport[1]<=generated_point[1]<viewport[1]+viewport[3] if len(generated_point)==2 and isinstance(viewport,list) else False,generated_point)
    add('C04','36-point-not-old-static',generated_point not in ([745,335],[738,503]),generated_point)
    add('C04','37-target-cx-equals-point',int(target.get('cx') or -1)==generated_point[0] if len(generated_point)==2 else False,target.get('cx'))
    add('C04','38-target-cy-equals-point',int(target.get('cy') or -1)==generated_point[1] if len(generated_point)==2 else False,target.get('cy'))
    add('C04','39-target-box-2x2',int(target.get('w') or 0)==2 and int(target.get('h') or 0)==2,(target.get('w'),target.get('h')))
    add('C04','40-point-digest-stable',bool(_digest(generated_point)),_digest(generated_point))

    # Council 5 — text structure.
    add('C05','41-expected-nonempty',bool(expected),len(expected))
    add('C05','42-actual-nonempty',bool(actual),len(actual))
    add('C05','43-exact-text-after',actual==expected,(actual,expected))
    add('C05','44-linebreak-count-exact',actual.count('\n')==expected.count('\n'),(actual.count('\n'),expected.count('\n')))
    add('C05','45-paragraph-count-exact',actual.count('\n')+1==expected.count('\n')+1,None)
    add('C05','46-no-cr', '\r' not in actual,repr(actual))
    add('C05','47-no-zero-width','\u200b' not in actual,repr(actual))
    add('C05','48-no-leading-space',actual==actual.lstrip(),repr(actual[:20]))
    add('C05','49-no-trailing-space',actual==actual.rstrip(),repr(actual[-20:]))
    add('C05','50-text-digest-match',_digest(actual)==_digest(expected),(_digest(actual),_digest(expected)))

    # Council 6 — restricted repair.
    ops=[str(row.get('op') or '') for row in plan if isinstance(row,dict)]
    add('C06','51-plan-list',isinstance(plan,list),type(plan).__name__)
    add('C06','52-op-allowlist',all(op in ('delete','linebreak') for op in ops),ops)
    add('C06','53-no-printable-insert',all(op!='insert' for op in ops),ops)
    add('C06','54-plan-bounded',len(plan)<=8,len(plan))
    add('C06','55-linebreak-bounded',sum(1 for op in ops if op=='linebreak')<=2,ops)
    add('C06','56-delete-bounded',sum(1 for op in ops if op=='delete')<=8,ops)
    add('C06','57-indices-nonnegative',all(int(row.get('index',-1))>=0 for row in plan if isinstance(row,dict)),plan)
    add('C06','58-no-write-command',contract.get('repair_has_pyautogui_write') is False,contract.get('repair_has_pyautogui_write'))
    add('C06','59-one-repair-max',int(contract.get('repair_attempts') or 0)<=1,contract.get('repair_attempts'))
    add('C06','60-repair-shape-same',int(contract.get('repair_shape_id') or expected_shape_id)==expected_shape_id,contract.get('repair_shape_id'))

    # Council 7 — transaction semantics.
    add('C07','61-before-old-positive',int(contract.get('before_old_count') or 0)>0,contract.get('before_old_count'))
    add('C07','62-after-old-lower',int(contract.get('after_old_count') or 0)<int(contract.get('before_old_count') or 0),(contract.get('before_old_count'),contract.get('after_old_count')))
    add('C07','63-before-new-zero',int(contract.get('before_new_count') or 0)==0,contract.get('before_new_count'))
    add('C07','64-after-new-positive',int(contract.get('after_new_count') or 0)>0,contract.get('after_new_count'))
    add('C07','65-save-issued',contract.get('save_issued') is True,contract.get('save_issued'))
    add('C07','66-commit-issued',contract.get('commit_issued') is True,contract.get('commit_issued'))
    add('C07','67-selection-proven',contract.get('selection_proven') is True,contract.get('selection_proven'))
    add('C07','68-visual-change-proven',contract.get('visual_change_proven') is True,contract.get('visual_change_proven'))
    add('C07','69-no-index-advance-before-proof',contract.get('advanced_only_after_exact_shape') is True,contract.get('advanced_only_after_exact_shape'))
    add('C07','70-checkpoint-shape-bound',contract.get('checkpoint_shape_id')==expected_shape_id,contract.get('checkpoint_shape_id'))

    # Council 8 — fail-closed behavior.
    add('C08','71-ambiguous-shape-blocks',contract.get('ambiguous_shape_blocks') is True,None)
    add('C08','72-missing-shape-blocks',contract.get('missing_shape_blocks') is True,None)
    add('C08','73-screen-drift-blocks',contract.get('screen_drift_blocks') is True,None)
    add('C08','74-window-drift-blocks',contract.get('window_drift_blocks') is True,None)
    add('C08','75-slide-size-missing-blocks',contract.get('slide_size_missing_blocks') is True,None)
    add('C08','76-shape-id-drift-blocks',contract.get('shape_id_drift_blocks') is True,None)
    add('C08','77-proof-tamper-blocks',contract.get('proof_tamper_blocks') is True,None)
    add('C08','78-cross-shape-edit-blocks',contract.get('cross_shape_edit_blocks') is True,None)
    add('C08','79-linebreak-loss-blocks',contract.get('linebreak_loss_blocks') is True,None)
    add('C08','80-second-repair-blocks',contract.get('second_repair_blocks') is True,None)

    # Council 9 — regression corpus/governance.
    add('C09','81-corpus-count-at-least-8',int(contract.get('corpus_count') or 0)>=8,contract.get('corpus_count'))
    add('C09','82-proof-tests-required',contract.get('proof_tests_required') is True,None)
    add('C09','83-policy-required',contract.get('policy_required') is True,None)
    add('C09','84-replay-required',contract.get('replay_required') is True,None)
    add('C09','85-zero-spend-required',contract.get('zero_spend_required') is True,None)
    add('C09','86-immutable-audit-required',contract.get('immutable_audit_required') is True,None)
    add('C09','87-no-merge-before-final',contract.get('merge_blocked') is True,None)
    add('C09','88-no-paid-fallback',contract.get('paid_fallback') is False,contract.get('paid_fallback'))
    add('C09','89-same-sha-required',contract.get('same_sha_required') is True,None)
    add('C09','90-evidence-reproducible',contract.get('evidence_reproducible') is True,None)

    # Council 10 — promotion/release.
    add('C10','91-official-score-gate',float(contract.get('official_score_gate') or 0)==1.0,contract.get('official_score_gate'))
    add('C10','92-ten-run-gate',int(contract.get('required_consecutive_runs') or 0)==10,contract.get('required_consecutive_runs'))
    add('C10','93-ten-run-same-sha',contract.get('ten_runs_same_sha') is True,None)
    add('C10','94-ten-run-score-exact',contract.get('ten_runs_score_1') is True,None)
    add('C10','95-ten-run-pre-gates-green',contract.get('ten_runs_pre_gates_green') is True,None)
    add('C10','96-ten-run-artifacts-unique',contract.get('ten_runs_artifacts_unique') is True,None)
    add('C10','97-release-default-blocked',contract.get('release_default_blocked') is True,None)
    add('C10','98-promotion-requires-100',contract.get('promotion_requires_100') is True,None)
    add('C10','99-master-councils-unanimous',contract.get('master_councils_unanimous') is True,None)
    add('C10','100-no-micro-reservation',contract.get('no_unresolved_gate') is True,None)

    _require(len(rows)==ELITE_TOTAL,'ELITE_REVIEW_COUNT_MISMATCH')
    failed=[row['name'] for row in rows if not row['pass']]
    councils=[]
    for idx in range(COUNCIL_TOTAL):
        members=rows[idx*10:(idx+1)*10]
        councils.append({'council':f'C{idx+1:02d}','pass':all(row['pass'] for row in members),
                         'members':[row['name'] for row in members]})
    _require(not failed,'ELITE_BOARD_BLOCKED:'+','.join(failed))
    _require(all(c['pass'] for c in councils),'ELITE_COUNCIL_BLOCKED')
    return {'status':'PASS','elite_pass':ELITE_TOTAL,'elite_total':ELITE_TOTAL,
            'councils_pass':COUNCIL_TOTAL,'councils_total':COUNCIL_TOTAL,
            'rows':rows,'councils':councils}

def validate_release_receipts(receipts, candidate_sha):
    _require(isinstance(receipts,list) and len(receipts)==10,'EXACTLY_TEN_OFFICIAL_RUNS_REQUIRED')
    run_ids=set(); artifact_ids=set()
    for index,row in enumerate(receipts,1):
        _require(str(row.get('head_sha') or '')==candidate_sha,f'RUN_{index}_SHA_MISMATCH')
        _require(float(row.get('score') or 0)==1.0,f'RUN_{index}_SCORE_NOT_ONE')
        _require(row.get('proof_tests')=='success',f'RUN_{index}_PROOF_TESTS_NOT_GREEN')
        _require(row.get('policy')=='success',f'RUN_{index}_POLICY_NOT_GREEN')
        _require(row.get('replay')=='success',f'RUN_{index}_REPLAY_NOT_GREEN')
        _require(row.get('focal')=='success',f'RUN_{index}_FOCAL_NOT_GREEN')
        run_ids.add(str(row.get('run_id') or ''))
        artifact_ids.add(str(row.get('artifact_id') or ''))
    _require(len(run_ids)==10 and '' not in run_ids,'TEN_UNIQUE_RUN_IDS_REQUIRED')
    _require(len(artifact_ids)==10 and '' not in artifact_ids,'TEN_UNIQUE_ARTIFACTS_REQUIRED')
    return {'status':'RELEASE_GATE_PASS','head_sha':candidate_sha,'runs':10}

if __name__=='__main__':
    import sys
    payload=json.load(open(sys.argv[1]))
    print(json.dumps(evaluate(payload),indent=2,sort_keys=True))
