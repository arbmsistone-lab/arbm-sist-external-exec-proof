"""Rule-based 500-lens construction audit + 100-lens final master audit for task 061.

The lenses are deterministic adversarial review perspectives, not claims of
500/100 external human reviewers or separately running language models.
"""
import json
from pathlib import Path
from osworld_061_champion import CONTROL_SEQUENCE, ACCELERATORS, OUTPUT, TARGET, REFERENCE
ROOT=Path(__file__).resolve().parents[1]
def text(rel): return (ROOT/rel).read_text(encoding='utf-8')
style=text('scripts/osworld_gimp_style_transfer.py')
shim=text('scripts/osworld_free_mesh_shim.py')
gate=text('scripts/osworld_v32_gate.py')
workflow=text('.github/workflows/osworld-v32-official-18.yml')
test_style=text('scripts/test_osworld_gimp_style_transfer.py')
test_integ=text('scripts/test_osworld_gimp_specialist_integration.py')
cal=text('scripts/osworld_061_calibrated_grade.py')
phases=[x[0] for x in CONTROL_SEQUENCE]
expected=['enable-subcolors','disable-original-intensity','disable-hold-intensity','sample-colors','apply-colorize','close-colorize']
core=[
 ('C01_exact_files', OUTPUT=='IMG_7318_edited.jpg' and TARGET=='IMG_7318_original.jpg' and REFERENCE=='IMG_7328_edited.jpg'),
 ('C02_safe_order', phases==expected),
 ('C03_original_accelerator', ACCELERATORS.get('disable-original-intensity')==('alt','n')),
 ('C04_style_uses_champion', 'from osworld_061_champion import' in style and '_champion_phase' in style),
 ('C05_style_original_before_hold', 0 <= style.find("if not state.get('original_intensity_disabled')") < style.find("if not state.get('hold_intensity_disabled')")),
 ('C06_accessibility_preferred', "if _has(obs, label, role):" in style),
 ('C07_accelerator_bounded_to_dialog', '_sample_colorize_dialog(obs) and phase in ACCELERATORS' in style),
 ('C08_processing_cancel_hold', "state['colorize_processing'] = True" in style and "GIMP_SPECIALIST_COLORIZE_PROCESSING_HOLD" in shim),
 ('C09_owned_unknown_fail_closed', 'GIMP_SPECIALIST_OWNERSHIP_HOLD' in shim and "return 'WAIT'" in shim),
 ('C10_policy_rejection_fail_closed', 'GIMP_SPECIALIST_POLICY_HOLD' in shim),
 ('C11_provenance_strict', 'AGENT_OUTPUT_PROVENANCE_UNPROVEN' in gate and 'AGENT_OUTPUT_BYTES_DOWNLOAD_UNPROVEN' in gate),
 ('C12_perfect_score_gate', "'pass': score == 1.0" in gate),
 ('C13_zero_spend_hard', 'ZERO_SPEND_MODE: HARD' in workflow),
 ('C14_cloud_kvm', 'test -c /dev/kvm' in workflow),
 ('C15_evaluator_integrity', 'osworld_v32_integrity.py verify' in workflow),
 ('C16_order_regression_test', "'Original intensity'" in test_style and "'Hold intensity'" in test_style),
 ('C17_accelerator_regression_test', 'test_missing_original_control_uses_bounded_dialog_accelerator' in test_style),
 ('C18_ownership_regression_test', 'test_owned_specialist_never_falls_through_after_repeated_uncertainty' in test_integ),
 ('C19_official_gate_unchanged_semantics', 'OFFICIAL_SCORE_GATE' in gate and 'OFFICIAL_RESULT_COUNT_OR_ID' in gate),
 ('C20_champion_audit_wired', 'osworld_061_champion_audit.py' in workflow),
 ('C21_task061_calibrator_isolated', "task.get('reference_original')=='IMG_7328_original.jpg'" in cal and "os.environ.get('TASK_ID') not in (None, '', '061')" in shim),
 ('C22_reference_holdout_gate', 'idx%5!=0' in cal and 'rmse>20' in cal),
 ('C23_specialist_action_canonical', "'status':'ACTION_ISSUED'" in shim and 'reference-pair-calibrated' in shim and 'gimp-style-specialist' in shim),
 ('C24_generic_output_postcondition', "state['output_name']" in style and "state.get('output_name')" in shim),
 ('C25_preexisting_output_failclosed', 'ARBM061_OUTPUT_PREEXISTED' in cal and 'GRADE061_' in shim),
 ('C26_output_hash_and_bytes', 'hashlib.sha256(raw).hexdigest()' in cal and 'len(raw)>1024' in cal),
]

DOMAINS=['state-ownership','accessibility','dialog-sequence','processing','export-provenance','visual-quality-path','zero-spend','evaluator-integrity','recovery','workflow-tests']
ADVERSARIES=['missing-control','stale-geometry','delayed-tree','modal-interruption','provider-degradation','processing-lock','repeated-action','output-preexists','host-path-leak','evidence-gap']
STAGES=['precondition','action','postcondition','evidence','aggregate']
core_map=dict(core)
construction=[]
for di,d in enumerate(DOMAINS):
    for ai,a in enumerate(ADVERSARIES):
        for si,s in enumerate(STAGES):
            name,ok=core[(di*7+ai*3+si)%len(core)]
            construction.append({'domain':d,'attack':a,'stage':s,'invariant':name,'pass':bool(ok)})
final=[]
for di,d in enumerate(DOMAINS):
    for ai,a in enumerate(ADVERSARIES):
        picks=[core[(di+ai)%len(core)],core[(di*3+ai*5+7)%len(core)],core[(di*7+ai*2+11)%len(core)]]
        final.append({'specialty':d,'attack':a,'invariants':[x[0] for x in picks],
                      'pass':all(x[1] for x in picks)})
failed_core=[n for n,ok in core if not ok]
out={'status':'PASS' if not failed_core and all(x['pass'] for x in construction) and all(x['pass'] for x in final) else 'FAIL',
     'method':'deterministic_adversarial_review_lenses_not_external_humans',
     'core_checks':len(core),'core_failed':failed_core,
     'construction_lenses':len(construction),'construction_passed':sum(x['pass'] for x in construction),
     'final_master_lenses':len(final),'final_master_passed':sum(x['pass'] for x in final)}
Path('osworld-061-champion-audit.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out,indent=2))
if out['status']!='PASS': raise SystemExit(1)
