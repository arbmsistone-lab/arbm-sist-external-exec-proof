"""Audit official evaluator evidence; successful process exit is insufficient."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
from osworld_evidence import seal, verify
from osworld_judge_audit import audit_judgements

SHARDS = {'A': ['001','019','037','055','073','091'], 'B': ['007','025','043','061','079','097'],
          'C': ['013','031','049','067','085','103']}
PINS = {'release': 'osworld-v2-2026.08.08', 'upstream_sha': 'd578d2d4e0dc82b43e270fdaa7fa89d9708cd154',
        'vm_revision': '8213366932c553e5fe758d0f2c8c8b81ffc3be8c',
        'vm_sha256': 'eb737ae70b49849e24af407de6a518439a23de05a8497096a948334ce0a909aa',
        'docker_digest': 'sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9',
        'task_manifest_sha256': '42f8f6f8939b8712997d5891456a575f8a2a5f53465e9e3e6747af5d6efd0915',
        'evaluator': 'OSWorld V2 official', 'max_steps': 500}


def audit_task(root, task, sha):
    verify(root)
    required = ['task-id.txt','candidate-sha.txt','release.txt','max-steps.txt','task-rc.txt',
                'osworld.log','shim.jsonl','shim-runtime.log','pins.json','zero-spend-mode.txt',
                'runner-environment.txt','evaluator-integrity.json']
    for name in required:
        if not (root / name).is_file(): raise ValueError('MISSING_EVIDENCE:' + name)
    def value(name): return (root / name).read_text(encoding='utf-8').strip()
    if value('task-id.txt') != task or value('candidate-sha.txt') != sha: raise ValueError('TASK_OR_SHA_MISMATCH')
    if value('release.txt') != PINS['release'] or value('max-steps.txt') != '500': raise ValueError('RELEASE_OR_STEPS_MISMATCH')
    if value('task-rc.txt') != '0': raise ValueError('TASK_PROCESS_FAILED')
    if value('zero-spend-mode.txt') != 'HARD' or value('runner-environment.txt') != 'github-hosted': raise ValueError('COST_OR_CLOUD_GATE')
    if json.loads(value('pins.json')) != PINS: raise ValueError('OFFICIAL_PINS_MISMATCH')
    integrity = json.loads(value('evaluator-integrity.json'))
    if not integrity or any(x['before'] != x['after'] for x in integrity.values()): raise ValueError('EVALUATOR_MODIFIED')
    results = list(root.glob('results/**/result.txt'))
    if len(results) != 1 or results[0].parent.name != task: raise ValueError('OFFICIAL_RESULT_COUNT_OR_ID')
    score = float(results[0].read_text().strip())
    if not math.isfinite(score) or not 0 <= score <= 1: raise ValueError('INVALID_OFFICIAL_SCORE')
    summaries = list(root.glob('results/**/results.json'))
    if len(summaries) != 1: raise ValueError('OFFICIAL_SUMMARY_COUNT')
    summary = json.loads(summaries[0].read_text())
    if len(summary) != 1 or summary[0].get('task_id') != task or summary[0].get('status') != 'success' or summary[0].get('score') != score:
        raise ValueError('OFFICIAL_EVALUATOR_SUMMARY_MISMATCH')
    telemetry = [json.loads(line) for line in value('shim.jsonl').splitlines()]
    issued = False
    for event in telemetry:
        if event.get('commit') != sha or event.get('task_id') != task: raise ValueError('SHIM_PROVENANCE_MISMATCH')
        if event.get('status') in ('SHIM_ERROR', 'TERMINAL_FAIL'): raise ValueError('FATAL_SHIM:' + str(event.get('reason')))
        if 'http' in event:
            if event.get('mandatory_cost_usd') != 0 or event.get('paid_fallback_used') is not False: raise ValueError('ZERO_SPEND_UNPROVEN')
            for attempt in event.get('provider_attempts', []):
                if attempt.get('status') == 200 and not (attempt.get('free_plan_proven') is True or attempt.get('zero_spend_confirmed') is True):
                    raise ValueError('FREE_PROVIDER_UNPROVEN')
        issued |= event.get('status') == 'ACTION_ISSUED'
    if not issued: raise ValueError('NO_REAL_AGENT_ACTION')
    judges=audit_judgements(root,task,sha)
    return {'task_id': task, 'score': score, 'pass': score == 1.0,
            'judge_audit':judges,
            'evidence_manifest_sha256': hashlib.sha256((root / 'SHA256SUMS.txt').read_bytes()).hexdigest()}


def aggregate(root, sha, focal=False):
    expected = ['061'] if focal else [task for group in SHARDS.values() for task in group]
    dirs = list(root.rglob('task-id.txt'))
    actual = [path.read_text().strip() for path in dirs]
    if sorted(actual) != sorted(expected):
        Path('osworld-v32-official18-summary.json').write_text(json.dumps({'status':'NOT PROVEN',
            'candidate_sha':sha,'expected_tasks':expected,'found_tasks':actual,'failure':'OFFICIAL_TASK_SET'},indent=2))
        raise ValueError('OFFICIAL_TASK_SET:' + json.dumps(actual))
    rows = []
    for path in sorted(dirs): rows.append(audit_task(path.parent, path.read_text().strip(), sha))
    passed = sum(row['pass'] for row in rows)
    out = {'status': ('FOCAL_061_PASS' if focal else 'OFFICIAL18_SCORES_PASS') if passed == len(expected) else 'NOT PROVEN',
           'candidate_sha': sha, 'official_tasks': len(expected), 'binary_successes': passed, 'tasks': rows, 'pins': PINS,
           'zero_spend_mode': 'HARD', 'heavy_local': 0}
    Path('osworld-v32-official18-summary.json').write_text(json.dumps(out, indent=2) + '\n')
    if passed != len(expected): raise ValueError('OFFICIAL_SCORE_GATE:' + json.dumps(out))
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('mode', choices=['seal','task','aggregate'])
    parser.add_argument('root', type=Path); parser.add_argument('--task'); parser.add_argument('--sha', default=os.environ.get('GITHUB_SHA'))
    parser.add_argument('--focal', action='store_true'); args = parser.parse_args()
    if args.mode == 'seal': seal(args.root)
    elif args.mode == 'task':
        row = audit_task(args.root, args.task, args.sha); print(json.dumps(row))
        if not row['pass']: raise SystemExit('OFFICIAL_SCORE_BELOW_ONE')
    else: print(json.dumps(aggregate(args.root, args.sha, args.focal)))
