"""FREE admission and evidence tooling; no benchmark evaluator internals."""
import argparse
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import time
import types
import urllib.request
from collections import Counter
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load_agent():
    if 'mm_agents.gemini_action_parser' not in sys.modules:
        sys.modules.setdefault('mm_agents', types.ModuleType('mm_agents'))
        spec = importlib.util.spec_from_file_location('mm_agents.gemini_action_parser', ROOT / 'vendor-gemini-action-parser.py')
        parser = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = parser
        spec.loader.exec_module(parser)
    spec = importlib.util.spec_from_file_location('g3_free_adapter', ROOT / 'g3-openrouter-free-adapter.py')
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)
    return agent


def safe_model_path(model):
    return re.sub(r'[^A-Za-z0-9._-]', '__', model)


def quota_admission(root=ROOT, now_ms=None):
    path = root / 'g3-free-quota-lock.json'
    if not path.exists():
        return
    lock = json.loads(path.read_text())
    receipt = (root / lock['receipt_path']).resolve()
    if not receipt.is_relative_to(root.resolve()):
        raise RuntimeError('G3_FREE_QUOTA_PROOF_INVALID')
    if hashlib.sha256(receipt.read_bytes()).hexdigest() != lock['receipt_sha256']:
        raise RuntimeError('G3_FREE_QUOTA_PROOF_INVALID')
    proof = json.loads(receipt.read_text())
    reset = int(proof['quota_headers']['x-ratelimit-reset'])
    if (proof['quota_scope'] != 'FREE_REQUESTS_PER_DAY' or
            proof['quota_headers']['x-ratelimit-remaining'] != '0' or
            proof['http_status'] != 429 or reset != lock['not_before_unix_ms']):
        raise RuntimeError('G3_FREE_QUOTA_PROOF_INVALID')
    if (int(time.time() * 1000) if now_ms is None else now_ms) < reset:
        raise RuntimeError('G3_FREE_DAILY_QUOTA_BLOCKED_UNTIL_' + lock['reset_utc'])


def write_json(path, data):
    Path(path).write_bytes((json.dumps(data, indent=2, allow_nan=False) + '\n').encode())


def journal_report(path, close_interrupted=False):
    path = Path(path)
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
    def key(row):
        return (row.get('run_id'), row.get('SHA'), row.get('task'), row.get('call_index'))
    starts = Counter(key(r) for r in rows if r.get('event') == 'request_started')
    terminals = Counter(key(r) for r in rows if r.get('event') in ('request_completed', 'request_failed_classified'))
    if close_interrupted:
        for row in list(rows):
            if row.get('event') == 'request_started' and terminals[key(row)] == 0:
                failed = {**row, 'event': 'request_failed_classified', 'request_state': 'TERMINAL',
                          'reason': 'PROCESS_INTERRUPTED_AFTER_START', 'terminal_state': 'BLOCKED',
                          'action_status': 'NOT_ISSUED', 'zero_spend': None,
                          'recovered_after_process_exit': True, 'observed_usage_available': False}
                with path.open('a', encoding='utf-8') as out:
                    out.write(json.dumps(failed) + '\n')
                    out.flush()
                    os.fsync(out.fileno())
                rows.append(failed)
                terminals[key(row)] += 1
    completed = [r for r in rows if r.get('event') == 'request_completed']
    failed = [r for r in rows if r.get('event') == 'request_failed_classified']
    complete = starts == terminals and all(n == 1 for n in starts.values())
    costs_valid = all(r.get('zero_spend') is True and r.get('reported_cost_usd') is not None and
                      Decimal(str(r['reported_cost_usd'])) == 0 and
                      r.get('returned_model') == r.get('requested_model') for r in completed)
    return {'accounting_complete': complete, 'started': sum(starts.values()),
            'journal_state': 'RECONCILED' if starts else 'NO_REQUESTS_STARTED',
            'completed': len(completed), 'failed_classified': len(failed),
            'structural_rejections': sum(r.get('structural_valid') is False for r in completed),
            'pending_requests': sum((starts - terminals).values()),
            'observed_completed_calls_zero_cost': costs_valid and bool(completed),
            'all_calls_observed_zero_cost': costs_valid and bool(completed) and not failed,
            'zero_spend_contract': all(r.get('zero_spend_contract') is True for r in rows),
            'execution_blocked': any(r.get('terminal_state') == 'BLOCKED' for r in rows),
            'failure_reasons': dict(Counter(r.get('reason') for r in failed))}


def catalog_admission(model):
    agent = load_agent()
    if model not in agent.ALLOWED_MODELS:
        raise RuntimeError('MODEL_NOT_ALLOWLISTED')
    with urllib.request.urlopen('https://openrouter.ai/api/v1/models', timeout=20) as response:
        models = json.load(response)['data']
    item = next((r for r in models if r['id'] == model), None)
    if not item or not model.endswith(':free'):
        raise RuntimeError('FREE_MODEL_NOT_AVAILABLE')
    if (not {'prompt', 'completion'} <= item['pricing'].keys() or
            any(Decimal(str(v)) != 0 for v in item['pricing'].values())):
        raise RuntimeError('FREE_PRICING_NOT_PROVEN')
    if ('image' not in item['architecture']['input_modalities'] or
            not {'tools', 'tool_choice', 'max_tokens'} <= set(item['supported_parameters']) or
            item['context_length'] < 32768):
        raise RuntimeError('FREE_CAPABILITY_NOT_ADVERTISED')
    return {k: item[k] for k in ('id', 'pricing', 'architecture', 'supported_parameters', 'context_length')}


def probe(model, output):
    """A new contract probe before VM; synthetic image, never task answers."""
    from PIL import Image, ImageDraw
    record = {'requested_model': model, 'state': 'BLOCKED', 'HEAVY_LOCAL': 0,
              'run_id': os.environ.get('GITHUB_RUN_ID'), 'SHA': os.environ.get('GITHUB_SHA')}
    try:
        quota_admission()
        record['catalog'] = catalog_admission(model)
        os.environ['ARBM_G3_FREE_MODEL'] = model
        os.environ['ARBM_G3_TASK_ID'] = 'capability-probe'
        agent = load_agent().ArbmG3Agent()
        canvas = Image.new('RGB', (400, 240), 'white')
        draw = ImageDraw.Draw(canvas)
        draw.rectangle((220, 60, 300, 140), fill='red')
        draw.ellipse((30, 140, 80, 190), fill='blue')
        image = io.BytesIO()
        canvas.save(image, format='PNG')
        marker = hashlib.sha256(os.urandom(16)).hexdigest()[:12]
        instruction = ('Retain this reference in state_summary: ' + marker + '.\n' +
                       'Context capability check. ' * 150 + '\nInspect the image. Use click at the center '
                       'of the red rectangle. This is a proposal only; no GUI is connected.')
        text, _ = agent.predict(instruction, {'screenshot': image.getvalue()})
        action = json.loads(text)
        params = action['parameters']
        if (action['action'] != 'click' or not 550 <= params['x'] <= 750 or
                not 250 <= params['y'] <= 585 or marker not in action['state_summary']):
            raise RuntimeError('IMAGE_CONTEXT_GROUNDING_PROBE_FAILED')
        report = journal_report(os.environ['ARBM_G3_USAGE_LOG'])
        if not report['accounting_complete'] or not report['all_calls_observed_zero_cost']:
            raise RuntimeError('PROBE_USAGE_NOT_PROVEN')
        record.update(state='PASS', journal=report, action=action, zero_spend=True,
                      capability=['IMAGE', 'TOOL_CALLING', 'CONTEXT', 'LATENCY', 'ZERO_SPEND'])
    except Exception as error:
        reason = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        record.update(reason=reason, zero_spend=None)
    finally:
        write_json(output, record)
    print(json.dumps({'state': record['state'], 'requested_model': model, 'reason': record.get('reason')}))
    return record['state'] == 'PASS'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['probe', 'journal'])
    parser.add_argument('--model', default='dots-studio/dots-3-note-preview:free')
    parser.add_argument('--output', required=True)
    parser.add_argument('--journal')
    args = parser.parse_args()
    if args.mode == 'probe':
        return 0 if probe(args.model, args.output) else 1
    result = journal_report(args.journal, close_interrupted=True)
    write_json(args.output, result)
    print(json.dumps(result))
    return 0 if result['accounting_complete'] and result['zero_spend_contract'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
