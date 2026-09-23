#!/usr/bin/env python3
"""Fail closed on task 091. Never infer success from a log word or reward."""
from __future__ import annotations
import argparse
import importlib
import json
import re
import sys
import time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from arbm091.trace_gate import require, verify_trace


def read_text(root: Path, name: str) -> str:
    path = root / name
    require(path.is_file() and not path.is_symlink(), 'MISSING_EVIDENCE:' + name)
    return path.read_text(encoding='utf-8').strip()


SEMANTIC_REQUIRED_STATUSES = (
    'TASK091_CONTRACT_VALIDATED=PASS',
    'TASK091_TARGET_RESOLVED=PASS',
    'TASK091_TARGET_UNIQUE=PASS',
    'TASK091_PRECONDITION=PASS',
    'TASK091_MUTATION_AUTHORIZED=PASS',
    'TASK091_MUTATION=PASS',
    'TASK091_SAVE=PASS',
    'TASK091_ROUNDTRIP=PASS',
    'TASK091_STRUCTURAL_DIFF=PASS',
    'TASK091_DIFF_BUDGET_EXACT=PASS',
    'TASK091_NO_COLLATERAL_MUTATION=PASS',
    'TASK091_SEMANTIC_RESULT=PASS',
)

LEGACY_091_PHASE_FRAGMENTS = (
    'table-cell-caret', 'move-table-caret', 'normalize-wps-terminal-marker',
    'select-table-container', 'table-reselect-container',
    'table-cell-text-hit', 'enter-table-cell-caret',
    'repair-atomic-pending-target', 'recover-nonpersisted-text-selection',
)


def verify_semantic_architecture(root: Path) -> dict:
    path=root/'shim.jsonl'
    require(path.is_file() and not path.is_symlink(), 'SEMANTIC_SHIM_LOG_MISSING')
    events=[json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    statuses={str(event.get('status') or '') for event in events}
    missing=[value for value in SEMANTIC_REQUIRED_STATUSES if value not in statuses]
    require(not missing, 'TASK091_SEMANTIC_EVIDENCE_MISSING:'+','.join(missing))
    require('TASK091_SEMANTIC_TEXT_TRANSACTIONS_COMPLETE' in statuses,
            'TASK091_SEMANTIC_TEXT_COMPLETION_MISSING')
    require('TASK091_SECTION_E_FORMAT_VERIFIED' in statuses,
            'TASK091_SECTION_E_SEMANTIC_COMPLETION_MISSING')
    for event in events:
        reason=str(event.get('reason') or '')
        phase=str(event.get('phase') or '')
        require('CARET_' not in reason and 'CARET_NOT' not in reason,
                'TASK091_CARET_DECISION_REAPPEARED:'+reason[:120])
        require(not any(fragment in phase for fragment in LEGACY_091_PHASE_FRAGMENTS),
                'TASK091_LEGACY_PHASE_EXECUTED:'+phase)
        if event.get('status')=='TASK091_SPECIALIST_ACTION_ISSUED':
            require(event.get('pending_edit') in (None,{}),
                    'TASK091_LEGACY_PENDING_EDIT_EXECUTED')
    return {
        'status':'TASK091_SEMANTIC_ARCHITECTURE_PASS',
        'required_statuses':list(SEMANTIC_REQUIRED_STATUSES),
        'semantic_completion':True,
        'section_e_semantic_completion':True,
        'legacy_phase_count':0,
        'caret_decision_count':0,
    }


def scan_fatal(root: Path, final: bool = False) -> None:
    path = root / 'shim.jsonl'
    if path.exists():
        data = path.read_bytes()
        complete = data.splitlines(keepends=True)
        for index, line in enumerate(complete):
            if not line.endswith(b'\n'):
                require(not final and index == len(complete) - 1, 'SHIM_LOG_TRUNCATED')
                continue
            event = json.loads(line)
            if event.get('status') in ('SHIM_ERROR', 'TERMINAL_FAIL'):
                raise ValueError('FATAL_SHIM:' + str(event.get('reason', 'UNKNOWN')))
    log = root / 'osworld.log'
    if log.is_file() and 'FATAL_SHIM:NO_PROGRESS_TIMEOUT' in log.read_text(encoding='utf-8'):
        raise ValueError('FATAL_SHIM:NO_PROGRESS_TIMEOUT')


def exact_result(root: Path, sha: str) -> dict:
    require(read_text(root, 'candidate-sha.txt') == sha, 'CANDIDATE_SHA_MISMATCH')
    require(read_text(root, 'task-id.txt') == '091', 'TASK_ID_MISMATCH')
    require(read_text(root, 'task-rc.txt') == '0', 'TASK_PROCESS_FAILED')
    paths = list(root.glob('results/**/result.txt'))
    require(len(paths) == 1 and paths[0].parent.name == '091', 'RESULT_COUNT_OR_TASK_MISMATCH')
    require(not paths[0].is_symlink(), 'RESULT_SYMLINK_FORBIDDEN')
    try:
        score = Decimal(paths[0].read_text().strip())
    except InvalidOperation as exc:
        raise ValueError('INVALID_OFFICIAL_SCORE') from exc
    require(score.is_finite() and score == Decimal('1.0'), 'OFFICIAL_SCORE_NOT_EXACTLY_ONE')
    summaries = list(root.glob('results/**/results.json'))
    require(len(summaries) == 1 and not summaries[0].is_symlink(), 'SUMMARY_COUNT_INVALID')
    summary = json.loads(summaries[0].read_text(), parse_float=Decimal)
    require(isinstance(summary, list) and len(summary) == 1, 'SUMMARY_SCHEMA_INVALID')
    row = summary[0]
    require(isinstance(row, dict) and row.get('task_id') == '091'
            and row.get('status') == 'success', 'OFFICIAL_SUMMARY_NOT_SUCCESS')
    value = row.get('score')
    require(type(value) in (Decimal, int) and value == Decimal('1.0'), 'SUMMARY_SCORE_NOT_EXACTLY_ONE')
    return {'task_id': '091', 'score': '1.0'}


def certify(root: Path, sha: str, run_id: str, run_attempt: str) -> dict:
    scan_fatal(root, final=True)
    exact_result(root, sha)
    require(read_text(root, 'run-id.txt') == run_id, 'RUN_ID_MISMATCH')
    require(read_text(root, 'run-attempt.txt') == run_attempt, 'RUN_ATTEMPT_MISMATCH')
    # Do not rewrite the official gate or reduce its checks.
    gate = importlib.import_module('osworld_v32_gate')
    audited = gate.audit_task(root, '091', sha)
    require(audited.get('pass') is True and audited.get('score') == 1.0, 'EXISTING_V32_GATE_FAILED')
    trace = verify_trace(root, sha, run_id, run_attempt)
    semantic = verify_semantic_architecture(root)
    # Independent action issued -> actually executed binding.
    events = [json.loads(line) for line in read_text(root, 'shim.jsonl').splitlines()]
    issued = {event['step']: event.get('command') for event in events
              if event.get('status') == 'ACTION_ISSUED'}
    from osworld_control import canonical_action
    for line in (root / 'wps-trace.jsonl').read_text().splitlines():
        row = json.loads(line)
        source = issued.get(row['step'])
        require(isinstance(source, str), 'TRACE_ACTION_NOT_ISSUED')
        canon = canonical_action({'action': 'exec', 'command': source})['command']
        require(canon == row.get('source_command'), 'ISSUED_EXECUTED_COMMAND_MISMATCH')
        require(row['command'] in canon.splitlines(), 'EXECUTED_ATOM_NOT_ISSUED')
    print('TASK091_EVALUATOR=PASS', file=sys.stderr, flush=True)
    return {'status': 'FOCAL_091_SCORE_ONE_WPS_TRACE_AND_SEMANTIC_PASS', 'candidate_sha': sha,
            'run_id': run_id, 'run_attempt': run_attempt, 'official': audited,
            'wps': trace, 'semantic': semantic}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--sha', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--run-attempt', required=True)
    parser.add_argument('--watch', action='store_true')
    parser.add_argument('--timeout-seconds', type=int, default=2700)
    parser.add_argument('--poll-seconds', type=float, default=2.0)
    args = parser.parse_args()
    try:
        require(re.fullmatch(r'[0-9a-f]{40}', args.sha) is not None, 'FULL_COMMIT_SHA_REQUIRED')
        require(args.run_id.isdigit() and args.run_attempt.isdigit(), 'RUN_PROVENANCE_REQUIRED')
        require(0 < args.timeout_seconds <= 5400 and 0.5 <= args.poll_seconds <= 30,
                'BOUNDED_MONITOR_REQUIRED')
        deadline = time.monotonic() + args.timeout_seconds
        while True:
            scan_fatal(args.root)
            receipt = args.root.with_name(args.root.name + '.complete.json')
            complete = receipt.is_file()
            if complete:
                meta = json.loads(receipt.read_text())
                require(meta == {'candidate_sha': args.sha, 'run_id': args.run_id,
                                 'run_attempt': args.run_attempt}, 'COMPLETION_PROVENANCE_MISMATCH')
                result = certify(args.root, args.sha, args.run_id, args.run_attempt)
                print(json.dumps(result, sort_keys=True))
                return 0
            if not args.watch:
                raise ValueError('RUN_NOT_FINALIZED')
            if time.monotonic() >= deadline:
                raise ValueError('SCORE_TRACKER_TIMEOUT')
            print(json.dumps({'status': 'RUNNING_NOT_CERTIFIED', 'task_id': '091'}), flush=True)
            time.sleep(args.poll_seconds)
    except Exception as exc:
        print(json.dumps({'status': 'FAIL', 'reason': str(exc), 'type': type(exc).__name__}),
              file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
