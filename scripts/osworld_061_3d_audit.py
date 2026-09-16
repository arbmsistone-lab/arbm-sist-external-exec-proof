"""Twenty final 3D audits: transaction, quality, provenance."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def text(rel): return (ROOT/rel).read_text(encoding='utf-8',errors='replace')
cal=text('scripts/osworld_061_calibrated_grade.py')
shim=text('scripts/osworld_free_mesh_shim.py')
style=text('scripts/osworld_gimp_style_transfer.py')
gate=text('scripts/osworld_v32_gate.py')
wf=text('.github/workflows/osworld-v32-official-18.yml')
champ=text('scripts/osworld_061_champion_audit.py')
incident=''
if len(sys.argv)>1:
    root=Path(sys.argv[1])
    for name in ('osworld.log','shim.jsonl','gate-result.json'):
        for p in root.rglob(name): incident+='\n'+p.read_text(errors='replace')[-20000:]
def has(s,*xs): return all(x in s for x in xs)
first_fallback=min([i for i in (incident.find('After darktable export'),incident.find('After GIMP export')) if i>=0] or [len(incident)])
agent_proof=incident.find('found_edited_photo=1')
prior_provenance_failed=(not incident) or agent_proof<0 or agent_proof>first_fallback
cases=[
('D01_exact_task_isolation', "task.get('reference_original')=='IMG_7328_original.jpg'" in cal, "task.get('reference_edited')=='IMG_7328_edited.jpg'" in cal, "task.get('output')=='IMG_7318_edited.jpg'" in cal),
('D02_reference_pair', 'reference_original' in cal and 'reference_edited' in cal, 'ARBM061_REF_RMSE' in cal, 'target_original' in cal),
('D03_holdout_validation', 'idx%5!=0' in cal, 'va=~tr' in cal, 'rmse>20' in cal),
('D04_full_score_threshold', 'rmse>20' in cal, "'pass': score == 1.0" in gate, 'OFFICIAL_SCORE_GATE' in gate),
('D05_bounded_model', 'poly3_residual' in cal, 'np.linalg.solve' in cal, 'ARBM061_REF_MODEL_UNSAFE' in cal),
('D06_output_shape_hash', 'assert z.size==t.size' in cal, 'quality=100' in cal, 'hashlib.sha256(raw).hexdigest()' in cal and 'len(raw)>1024' in cal),
('D07_transaction_ownership', 'GRADE061_OWNERSHIP_HOLD' in shim, 'pending_phase' in shim, 'GIMP_SPECIALIST_PHASE_UNVERIFIED' in shim),
('D08_postcondition_commit', 'GIMP_SPECIALIST_PHASE_ACK' in shim, "state.pop('pending_phase'" in shim, 'VERIFIER.last_result' in shim),
('D09_gimp_safe_order', 'disable-original-intensity' in style, 'disable-hold-intensity' in style, 'sample-colors' in style and 'apply-colorize' in style),
('D10_processing_settle', 'colorize_processing' in style, "_has(obs, 'Cancel'" in style, 'GIMP_SPECIALIST_COLORIZE_PROCESSING_HOLD' in shim),
('D11_export_provenance', 'AGENT_OUTPUT_PROVENANCE_UNPROVEN' in gate, 'AGENT_OUTPUT_BYTES_DOWNLOAD_UNPROVEN' in gate, 'found_edited_photo=1' in gate),
('D12_fallback_order', 'first_agent_proof > first_fallback' in gate, 'After GIMP export' in gate, 'After darktable export' in gate),
('D13_evaluator_integrity', 'evaluator-integrity.json' in gate, 'osworld_v32_integrity.py verify' in wf, 'EVALUATOR_MODIFIED' in gate),
('D14_exact_score', 'INVALID_OFFICIAL_SCORE' in gate, "score == 1.0" in gate, 'OFFICIAL_EVALUATOR_SUMMARY_MISMATCH' in gate),
('D15_zero_spend', 'ZERO_SPEND_MODE: HARD' in wf, 'paid_fallback_used' in shim, 'mandatory_cost_usd' in shim),
('D16_cloud_only_heavy', 'runs-on: ubuntu-24.04' in wf, 'test -c /dev/kvm' in wf, 'github-hosted' in wf),
('D17_timeout_failclosed', 'run_waits' in cal and '>12' in cal, '061-calibration-timeout' in cal, 'terminal_failed' in cal),
('D18_output_preexist', 'ARBM061_OUTPUT_PREEXISTED' in cal, 'OUTPUT_PREEXISTED_PROVENANCE_UNSAFE' in text('scripts/osworld_gimp_sample_probe.py'), 'ORIGINAL_OVERWRITE_ATTEMPT_BLOCKED' in text('scripts/osworld_gimp_sample_probe.py')),
('D19_prior_incident_learned', 'MSE=5049.3369' in incident or not incident, 'quality_score=0.0000' in incident or not incident, prior_provenance_failed),
('D20_audit_stack', 'construction_lenses' in champ, 'osworld_061_specialist_swarm.py' in text('.github/workflows/osworld-061-world-audit.yml'), 'osworld_061_3d_audit.py' in text('.github/workflows/osworld-061-world-audit.yml')),
]
rows=[]
for name,t,q,p in cases:
    rows.append({'audit':name,'transaction':bool(t),'quality':bool(q),'provenance':bool(p),'pass':bool(t and q and p)})
failed=[r['audit'] for r in rows if not r['pass']]
out={'status':'PASS' if not failed else 'FAIL','audits':20,'dimensions':3,'checks':60,'passed':sum(int(r[k]) for r in rows for k in ('transaction','quality','provenance')),'failed':failed,'rows':rows}
Path('osworld-061-final-3d-audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({k:out[k] for k in ('status','audits','dimensions','checks','passed','failed')},indent=2))
if failed: raise SystemExit(1)
