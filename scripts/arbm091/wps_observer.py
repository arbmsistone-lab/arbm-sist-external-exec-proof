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
import time
from pathlib import Path
from urllib.parse import urlparse
import requests
from osworld_control import canonical_action, task091_panel_target_proof
from arbm091.trace_gate import digest, parse_atom, pointer, preflight, postflight, require, inside

_LOCK = threading.Lock()
_PROBE = Path(__file__).with_name('guest_probe.py').read_text()


def _probe_once(controller, point):
    server = controller.http_server
    parsed = urlparse(server)
    require(parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1'),
            'PROBE_ISOLATED_GUEST_ONLY')
    code = "import os\nos.environ['TASK_ID'] = '091'\nPOINT = " + repr(point) + '\n' + _PROBE
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
    return payload, png
def _settled_probe(controller, point, attempts=4, delay=0.12):
    last = None
    for index in range(attempts):
        payload, png = _probe_once(controller, point)
        last = (payload, png)
        if payload.get('stable') is True:
            return payload, png
        if index + 1 < attempts:
            time.sleep(delay)
    payload, png = last
    require(payload.get('stable') is True, 'FOREGROUND_UNSTABLE')
    return payload, png


def snapshot(controller, root: Path, name: str, point, active_slide=None):
    server = controller.http_server
    parsed = urlparse(server)
    require(parsed.scheme == 'http' and parsed.hostname in ('localhost', '127.0.0.1'),
            'PROBE_ISOLATED_GUEST_ONLY')
    payload, png = _settled_probe(controller, point)
    if type(active_slide) is int and active_slide > 0:
        payload['active_slide'] = active_slide
    raw = (json.dumps(payload, sort_keys=True) + '\n').encode()
    directory = root / 'wps-observations'
    directory.mkdir(parents=True, exist_ok=True)
    metadata_path = directory / (name + '.json')
    screenshot_path = directory / (name + '.png')
    require(not metadata_path.exists() and not screenshot_path.exists(), 'EVIDENCE_OVERWRITE_FORBIDDEN')
    metadata_path.write_bytes(raw)
    screenshot_path.write_bytes(png)
    operational = {
        'schema': 1,
        'source': name,
        'stable': payload.get('stable') is True,
        'captured_monotonic_ns': payload.get('captured_monotonic_ns'),
        'window': payload.get('window', {}),
        'controls': payload.get('controls', []),
        'focused_control': payload.get('focused_control'),
        'active_slide': payload.get('active_slide'),
        'deck_slide_text': payload.get('deck_slide_text', {}),
        'deck_slide_runs': payload.get('deck_slide_runs', {}),
        'deck_slide_shapes': payload.get('deck_slide_shapes', {}),
        'deck_slide_charts': payload.get('deck_slide_charts', {}),
        'deck_slide_relationships': payload.get('deck_slide_relationships', {}),
        'deck_file': payload.get('deck_file', {}),
        'slide_canvas_bbox': payload.get('slide_canvas_bbox'),
        'screen': payload.get('screen', []),
        'screenshot_sha256': hashlib.sha256(png).hexdigest(),
    }
    operational_raw=(json.dumps(operational, sort_keys=True) + '\n').encode()
    operational_path=root / 'window-state.json'
    temporary=root / ('.window-state-' + str(os.getpid()) + '.tmp')
    temporary.write_bytes(operational_raw)
    os.replace(temporary, operational_path)
    return payload, {'metadata': str(metadata_path.relative_to(root)),
                     'metadata_sha256': hashlib.sha256(raw).hexdigest(),
                     'screenshot': str(screenshot_path.relative_to(root)),
                     'screenshot_sha256': hashlib.sha256(png).hexdigest()}


def _read_window_state(root: Path):
    path=root/'window-state.json'
    if not path.is_file():
        return None
    try:
        value=json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    return value if isinstance(value,dict) else None


def _consume_panel_envelope(root: Path, command: str, prior: dict, before: dict, point):
    path=root/'pending-panel-target.json'
    if not path.is_file():
        return None
    try:
        envelope=json.loads(path.read_text(encoding='utf-8'))
        require(isinstance(envelope,dict) and envelope.get('schema')==1,'TASK091_PANEL_ENVELOPE_SCHEMA_INVALID')
        require(str(envelope.get('candidate_sha') or '')==str(os.environ.get('GITHUB_SHA') or ''),'TASK091_PANEL_ENVELOPE_SHA_MISMATCH')
        require(str(envelope.get('command') or '')==str(command or ''),'TASK091_PANEL_ENVELOPE_COMMAND_MISMATCH')
        signed=envelope.get('target')
        require(isinstance(signed,dict) and str(signed.get('source') or '').casefold()=='task091-panel-canonical','TASK091_PANEL_SIGNED_TARGET_MISSING')
        require(task091_panel_target_proof(signed)==str(signed.get('proof_sha256') or ''),'TASK091_PANEL_SIGNATURE_INVALID')
        require(isinstance(prior,dict)
                and str(prior.get('source') or '')==str(signed.get('source_observation_id') or '')
                and str(prior.get('screenshot_sha256') or '')==str(signed.get('screenshot_sha256') or ''),
                'TASK091_PANEL_STALE_SOURCE_FRAME')
        require((prior.get('window') or {}).get('bbox')==signed.get('window_bbox')
                and (before.get('window') or {}).get('bbox')==signed.get('window_bbox'),
                'TASK091_PANEL_WINDOW_FRAME_MISMATCH')
        observed=before.get('target')
        require(isinstance(observed,dict),'TASK091_PANEL_CONTROL_NOT_OBSERVED')
        require(observed.get('showing') is True and observed.get('enabled') is True,'TASK091_PANEL_CONTROL_NOT_INTERACTIVE')
        require(str(observed.get('label') or '').strip().casefold()==str(signed.get('label') or '').strip().casefold(),'TASK091_PANEL_CONTROL_IDENTITY_MISMATCH')
        require(str(observed.get('role') or '').strip().casefold()==str(signed.get('control_role') or '').strip().casefold(),'TASK091_PANEL_CONTROL_ROLE_MISMATCH')
        require(int(observed.get('pid') or 0)==int(signed.get('control_pid') or -1),'TASK091_PANEL_CONTROL_PID_MISMATCH')
        require(observed.get('bbox')==[int(signed[k]) for k in ('x','y','w','h')],'TASK091_PANEL_CONTROL_BOUNDS_MISMATCH')
        require(point==(int(signed.get('cx')),int(signed.get('cy'))) and inside(point,observed.get('bbox')),'TASK091_PANEL_POINT_OUTSIDE_PROVEN_BOUNDS')
        require(int(before.get('hit_owner_pid') or 0)==int(observed.get('pid') or -1)
                and int(before.get('hit_owner_id') or 0)>0,'TASK091_PANEL_HIT_OWNER_MISMATCH')
        return {'label':signed.get('label'),'role':signed.get('control_role'),
                'bbox':observed.get('bbox'),'pid':observed.get('pid'),
                'source_observation_id':signed.get('source_observation_id'),
                'proof_sha256':signed.get('proof_sha256')}
    finally:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


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



def _next_active_slide(command, current):
    name, args, kwargs = parse_atom(command)
    if name == 'hotkey' and {str(value).casefold() for value in args} == {'ctrl', 'home'}:
        return 1
    if name == 'press' and args and str(args[0]).casefold() in ('pagedown', 'pageup'):
        if type(current) is not int or current <= 0:
            return None
        presses = kwargs.get('presses', 1)
        if type(presses) is not int or presses < 1:
            return None
        delta = presses if str(args[0]).casefold() == 'pagedown' else -presses
        return max(1, current + delta)
    return current

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
        active_slide = getattr(self, '_arbm091_active_slide', None)

        def guarded_execute(command):
            nonlocal active_slide
            canonical = canonical_action({'action': 'exec', 'command': command})['command']
            result = None
            for substep, atom in enumerate(canonical.splitlines(), 1):
                row = {'kind': 'action', 'step': step, 'substep': substep,
                       'command': atom, 'source_command': canonical,
                       'command_sha256': hashlib.sha256(atom.encode()).hexdigest()}
                try:
                    point = pointer(atom)
                    prior=_read_window_state(root)
                    before, reference = snapshot(controller, root, f'{step:04d}-{substep:02d}-before', point, active_slide)
                    row['before'] = reference
                    panel_proof=_consume_panel_envelope(root,atom,prior,before,point)
                    if panel_proof is not None:
                        row['panel_target_proof']=panel_proof
                    row['scope'] = preflight(atom, before)
                    next_active_slide = _next_active_slide(atom, active_slide)
                    result = original_execute(atom)
                    require(isinstance(result, dict) and result.get('status') == 'success'
                            and result.get('returncode') == 0, 'GUEST_ACTION_FAILED_OR_UNACKNOWLEDGED')
                    after, reference = snapshot(controller, root, f'{step:04d}-{substep:02d}-after', None, next_active_slide)
                    postflight(atom, before, after)
                    active_slide = next_active_slide
                    self._arbm091_active_slide = active_slide
                    row['after'] = reference
                    row['before_window'] = before.get('window', {})
                    row['after_window'] = after.get('window', {})
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