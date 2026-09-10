"""Rebuild G3 usage and provenance from downloaded artifacts; no network/VM."""

import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

INPUT_RATE = Decimal('1.50')
OUTPUT_RATE = Decimal('9.00')


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def build(evidence, output):
    output.mkdir(parents=True, exist_ok=True)
    runs = json.loads((evidence / 'runs.json').read_text(encoding='utf-8-sig'))
    summaries = []
    total_cost = Decimal('0')
    for run in runs:
        run_id = str(run['databaseId'])
        root = evidence / run_id
        usage_files = list(root.rglob('g3-paid-usage.jsonl')) if root.exists() else []
        if len(usage_files) > 1:
            raise ValueError('Duplicate usage artifact; reconcile before accounting')
        rows = [json.loads(line) for path in usage_files for line in path.read_text().splitlines() if line]
        prompts = sum(r['prompt_tokens'] for r in rows)
        tokens = sum(r['total_tokens'] for r in rows)
        outputs = sum(r['output_tokens'] for r in rows)
        thoughts = sum(r['thought_tokens'] for r in rows)
        status = 'ARTIFACT_USAGE_RECORDED' if rows else 'USAGE_UNKNOWN'
        log_path = evidence / f'run-{run_id}.log'
        if not rows and log_path.exists() and 'probe' in run['workflowName']:
            log = log_path.read_text(encoding='utf-8-sig')
            values = {key: re.findall(r'Z ' + key + r'=(\d+)\s*$', log, re.MULTILINE)
                      for key in ('PROMPT_TOKENS', 'OUTPUT_TOKENS', 'TOTAL_TOKENS')}
            if all(len(matches) == 1 for matches in values.values()):
                prompts = int(values['PROMPT_TOKENS'][0])
                outputs = int(values['OUTPUT_TOKENS'][0])
                tokens = int(values['TOTAL_TOKENS'][0])
                thoughts = tokens - prompts - outputs
                status = 'PROBE_LOG_USAGE_RECORDED'
        cost = (prompts * INPUT_RATE + max(tokens - prompts, outputs + thoughts) * OUTPUT_RATE) / 1_000_000
        total_cost += cost
        result_files = list(root.rglob('result.txt')) if root.exists() else []
        scores = [p.read_text().strip() for p in result_files]
        trajectory_files = list(root.rglob('traj.jsonl')) if root.exists() else []
        trajectory = [json.loads(line) for p in trajectory_files for line in p.read_text().splitlines() if line]
        errors = [r for r in trajectory if 'Error' in r]
        depleted = any('prepayment credits are depleted' in str(r).lower() for r in errors)
        summary = {
            **run, 'url': f'https://github.com/arbmsistone-lab/arbm-sist-external-exec-proof/actions/runs/{run_id}',
            'usage_status': status, 'successful_calls_with_usage': len(rows) if rows else (1 if tokens else 0),
            'prompt_tokens': prompts if status != 'USAGE_UNKNOWN' else None,
            'output_tokens': outputs if status != 'USAGE_UNKNOWN' else None,
            'thought_or_other_output_tokens': max(tokens - prompts - outputs, thoughts) if status != 'USAGE_UNKNOWN' else None,
            'total_tokens': tokens if status != 'USAGE_UNKNOWN' else None,
            'recorded_cost_usd': str(cost) if status != 'USAGE_UNKNOWN' else None,
            'official_scores': scores, 'trajectory_rows': len(trajectory),
            'trajectory_errors': len(errors), 'provider_credit_depleted': depleted,
            'prompt_tokens_first': rows[0]['prompt_tokens'] if rows else None,
            'prompt_tokens_last': rows[-1]['prompt_tokens'] if rows else None,
            'prompt_tokens_max': max((r['prompt_tokens'] for r in rows), default=None),
            'usage_sha256': sha256(usage_files[0]) if usage_files else None,
        }
        summaries.append(summary)
    report = {
        'schema': 'arbm-g3-evidence-v1', 'state': 'BLOCKED_NOT_GREEN_PROVEN',
        'repository': 'arbmsistone-lab/arbm-sist-external-exec-proof',
        'branch': 'g3/paid-cert-lane-20260910',
        'candidate_sha': '06625444d3cdb45a93865daf91769f1c9ff44559',
        'run_sha': 'f26ba87020ceaefc01d22e0a592fbc864d0d9291',
        'benchmark_release': 'v2026.08.08',
        'benchmark_sha': 'd578d2d4e0dc82b43e270fdaa7fa89d9708cd154',
        'model': 'gemini-3.5-flash', 'authorized_total_usd': '5.00',
        'recorded_cost_usd': str(total_cost),
        'arithmetic_remainder_usd_not_spendable': str(Decimal('5.00') - total_cost),
        'reconciliation_complete': False,
        'unknown_usage_run_ids': [r['databaseId'] for r in summaries if r['usage_status'] == 'USAGE_UNKNOWN'],
        'pricing_source': 'https://ai.google.dev/gemini-api/docs/pricing',
        'pricing_usd_per_million': {'input': str(INPUT_RATE), 'output_including_thinking': str(OUTPUT_RATE)},
        'new_paid_runs_started': 0, 'new_model_calls_started': 0, 'heavy_local': 0,
        'runs': summaries,
    }
    (output / 'run-ledger.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    manifest = {p.relative_to(evidence).as_posix(): {'sha256': sha256(p), 'bytes': p.stat().st_size}
                for p in sorted(evidence.rglob('*')) if p.is_file()}
    (output / 'source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    ledger = {
        'schema': 'arbm-g3-paid-budget-v1', 'authorized_total_usd': '5.00',
        'recorded_usage_usd': str(total_cost), 'reconciled_total_usd': None,
        'reconciliation_status': 'INCOMPLETE', 'provider_credit_status': 'DEPLETED',
        'per_call_cost_bound_status': 'UNPROVEN',
        'reserved_run_usd': '0', 'accounted_run_ids': [],
        'observed_run_ids': [str(r['databaseId']) for r in runs],
        'audit_3x': {'A': 'PENDING_LOCAL_TESTS', 'B': 'PENDING_DIFF_AUDIT', 'C': 'BLOCKED'},
        'audited_files_sha256': {},
        'blockers': ['Probe 34511385723 returned HTTP 200 but discarded usage before assertion failure.',
                     'Run 34535970921 received eight credit-depleted rejections; no usage or official result.',
                     'Provider account credit/billing reconciliation is required; do not assume unlogged requests cost zero.',
                     'The per-call reserve is heuristic; a proven input/output cost bound is required before paid admission.',
                     'Official score, functional stability and complete certification remain unproven.'],
    }
    (output.parent / 'g3-paid-budget.json').write_text(json.dumps(ledger, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('recorded_cost_usd', 'arithmetic_remainder_usd_not_spendable', 'unknown_usage_run_ids', 'state')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--evidence-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    build(args.evidence_root.resolve(), args.output.resolve())
