"""Instrument agent GUI calls without changing task/evaluator code or results.

Installed on DesktopEnv.step by the explicit, version-checked runtime adapter.
Each original GUI call still executes through the official controller. Metadata
collection uses a fixed read-only program, separate from the agent's program.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
import threading
from pathlib import Path
from urllib.parse import urlparse
import requests
from osworld_control import canonical_action
from arbm091.trace_gate import digest, pointer, preflight, require

_LOCK = threading.Lock()
_PROBE = Path(__file__).with_name('guest_probe.py').read_text()


def snapshot(controller, root: Path, name: str, point):
    server = controller.http_server
    parsed = urlparse(server)
    require(parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1'),
            'PROBE_ISOLATED_GUEST_ONLY')
    code = 'POINT = ' + repr(point) + '\n' + _PROBE
    session = requests.Session()
    session.trust_env = False
    try:
        response = session.post(server.rstrip('/') + '/execute',
                                json={'command': ['python3', '-c', code], 'shell': False},
                                timeout=(3, 15))
        response.raise_for_status()
        result = response.json()
    finally:
        session.close()
    require(result.get('returncode') == 0 and result.get('status') == 'success',
            'TRUSTED_GUEST_PROBE_FAILED:' + str(result.get('error', ''))[:160])
    payload = json.loads(str(result['output']).strip())
    png = base64.b64decode(payload.pop('screenshot_base64'), validate=True)
    raw = (json.dumps(payload, sort_keys=True) + '\n').encode()
    directory = root / 'wps-observations'
    directory.mkdir(parents=True, exist_ok=True)
    metadata_path = directory / (name + '.json')
    screenshot_path = directory / (name + '.png')
    require(not metadata_path.exists() and not screenshot_path.exists(), 'EVIDENCE_OVERWRITE_FORBIDDEN')
    metadata_path.write_bytes(raw)
    screenshot_path.write_bytes(png)
    return payload, {'metadata': str(metadata_path.relative_to(root)),
                     'metadata_sha256': hashlib.sha256(raw).hexdigest(),
                     'screenshot': str(screenshot_path.relative_to(root)),
                     'screenshot_sha256': hashlib.sha256(png).hexdigest()}


def append(root: Path, row: dict):
    with _LOCK:
        path = root / 'wps-trace.jsonl'
        previous = '0' * 64
        count = 0
        if path.exists():
            rows = path.read_text().splitlines()
            if rows:
                previous = json.loads(rows[-1])['event_sha256']
                count = len(rows)
        value = {'schema': 1, 'ordinal': count + 1, 'previous_sha256': previous,
                 'candidate_sha': os.environ['GITHUB_SHA'], 'task_id': os.environ['TASK_ID'],
                 'run_id': os.environ['GITHUB_RUN_ID'], 'run_attempt': os.environ['GITHUB_RUN_ATTEMPT'],
                 **row}
        value['event_sha256'] = digest(value)
        with path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(value, sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())


def install(environment_class):
    require(os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted'
            and os.environ.get('ZERO_SPEND_MODE') == 'HARD'
            and os.environ.get('TASK_ID') == '091', 'OBSERVER_REMOTE_ZERO_SPEND_TASK091_REQUIRED')
    if getattr(environment_class, '_arbm091_observed', False):
        return
    original_step = environment_class.step

    def observed_step(self, action, pause=2):
        root = Path(os.environ['ARBM_WPS_EVIDENCE_DIR'])
        root.mkdir(parents=True, exist_ok=True)
        step = int(self._step_no) + 1
        controller = self.controller
        original_execute = controller.execute_python_command

        def guarded_execute(command):
            canonical = canonical_action({'action': 'exec', 'command': command})['command']
            result = None
            for substep, atom in enumerate(canonical.splitlines(), 1):
                row = {'kind': 'action', 'step': step, 'substep': substep,
                       'command': atom, 'source_command': canonical,
                       'command_sha256': hashlib.sha256(atom.encode()).hexdigest()}
                try:
                    point = pointer(atom)
                    before, reference = snapshot(controller, root, f'{step:04d}-{substep:02d}-before', point)
                    row['before'] = reference
                    row['scope'] = preflight(atom, before)
                    result = original_execute(atom)
                    require(isinstance(result, dict) and result.get('status') == 'success'
                            and result.get('returncode') == 0, 'GUEST_ACTION_FAILED_OR_UNACKNOWLEDGED')
                    _, reference = snapshot(controller, root, f'{step:04d}-{substep:02d}-after', None)
                    row['after'] = reference
                    row.update(status='executed', returncode=0)
                    append(root, row)
                except Exception as exc:
                    append(root, {**row, 'status': 'blocked-or-unproven', 'reason': str(exc)[:240]})
                    raise
            return result

        controller.execute_python_command = guarded_execute
        try:
            return original_step(self, action, pause)
        finally:
            controller.execute_python_command = original_execute

    environment_class.step = observed_step
    environment_class._arbm091_observed = True
