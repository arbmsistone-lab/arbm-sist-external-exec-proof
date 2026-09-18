"""Opt-in WPS focus boundary for the official OSWorld GUI action bridge.

No guest filesystem reads, window-manager shell commands, evaluator changes or
score writes. Focus recovery is an ordinary, observed GUI action; activation
is not accepted until a later observation identifies WPS in the Ubuntu panel.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import threading
import time
from typing import Any

APP = 'wps presentation'
MAX_FOCUS_ATTEMPTS = 2
APP_CONTROLS = {
    APP, 'google chrome', 'chromium', 'firefox', 'firefox web browser',
    'mailhub', 'thunderbird mail', 'files', 'terminal', 'system',
    'show applications', 'show desktop', 'workspace switcher',
}
POINTERS = {'click', 'doubleClick', 'rightClick', 'moveTo', 'dragTo', 'mouseDown', 'mouseUp'}


def norm(value: Any) -> str:
    return re.sub(r'\s+', ' ', str(value or '').strip().strip('"')).casefold()


def nodes(observation: str) -> list[dict[str, Any]]:
    result = []
    for line in observation.splitlines():
        cols = line.split('\t')
        if len(cols) < 7:
            continue
        xy = re.fullmatch(r'\((-?\d+)\s*,\s*(-?\d+)\)', cols[-2].strip())
        wh = re.fullmatch(r'\((\d+)\s*,\s*(\d+)\)', cols[-1].strip())
        if not xy or not wh:
            continue
        x, y = map(int, xy.groups())
        w, h = map(int, wh.groups())
        if w > 0 and h > 0:
            result.append(dict(role=cols[0], label=(cols[1] or cols[2]).strip('"'),
                               x=x, y=y, w=w, h=h))
    return result


def observed_app(observation: str, *, allow_canonical_prefix: bool = False) -> str:
    apps = {norm(n['label']) for n in nodes(observation)
            if n['role'] == 'menu' and n['y'] == 0 and norm(n['label']) != 'system'}
    if len(apps) == 1:
        return next(iter(apps))
    if apps:
        raise ValueError('WPS_AMBIGUOUS_PANEL')
    if allow_canonical_prefix:
        prefix = 'ACTIVE APPLICATION (Ubuntu panel): '
        names = {norm(line[len(prefix):]) for line in observation.splitlines() if line.startswith(prefix)}
        if len(names) == 1:
            return next(iter(names))
    raise ValueError('WPS_FOREGROUND_UNPROVEN')


def focus_recovery(observation: str, attempts: int) -> dict[str, Any]:
    if attempts >= MAX_FOCUS_ATTEMPTS:
        raise ValueError('WPS_FOCUS_RECOVERY_EXHAUSTED')
    hits = {(n['x'], n['y'], n['w'], n['h']): n for n in nodes(observation)
            if n['role'] in {'push-button', 'toggle-button', 'button'}
            and norm(n['label']) == APP and n['x'] >= 0 and n['y'] >= 0}
    if len(hits) != 1:
        raise ValueError('WPS_FOCUS_TARGET_UNPROVEN')
    n = next(iter(hits.values()))
    return {'action': 'exec', 'command': f"pyautogui.click({n['x']+n['w']//2}, {n['y']+n['h']//2})",
            'target': {'source': 'accessibility', 'label': n['label'], 'role': n['role']},
            'plan': 'Activate the uniquely observed WPS launcher; verify the next Ubuntu panel observation.'}


def validate_action(action: dict[str, Any], observation: str, *, canonical: bool = False) -> None:
    if observed_app(observation, allow_canonical_prefix=canonical) != APP:
        raise ValueError('WPS_FOREGROUND_REQUIRED')
    target = action.get('target') if isinstance(action.get('target'), dict) else {}
    label = norm(target.get('label'))
    if label in APP_CONTROLS or re.search(r'\b(chrome|chromium|mailhub|firefox|thunderbird|terminal)\b', label):
        raise ValueError('WPS_EXTERNAL_TARGET_FORBIDDEN')
    if action.get('action') != 'exec':
        return
    tree = ast.parse(str(action.get('command') or ''))
    controls = nodes(observation)
    protected = [n for n in controls if n['role'] in {'menu', 'push-button', 'toggle-button', 'button'}
                 and norm(n['label']) in APP_CONTROLS]
    for stmt in tree.body:
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
            raise ValueError('WPS_DIRECT_GUI_CALL_REQUIRED')
        call = stmt.value
        if not (isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name)
                and call.func.value.id == 'pyautogui'):
            raise ValueError('WPS_DIRECT_GUI_CALL_REQUIRED')
        name = call.func.attr
        args = [ast.literal_eval(a) for a in call.args]
        kw = {k.arg: ast.literal_eval(k.value) for k in call.keywords}
        keys = {norm(a) for a in args if isinstance(a, str)}
        if args and isinstance(args[0], (list, tuple)):
            keys.update(norm(a) for a in args[0])
        forbidden = bool(keys & {'win', 'winleft', 'winright', 'super', 'command'})
        forbidden |= name in {'keyDown', 'keyUp'}
        forbidden |= name == 'hotkey' and (
            {'alt', 'tab'} <= keys or {'alt', 'f4'} <= keys or
            {'ctrl', 'q'} <= keys or {'ctrl', 'alt'} <= keys)
        if forbidden:
            raise ValueError('WPS_CONTEXT_SWITCH_FORBIDDEN')
        if name in POINTERS:
            if len(args) >= 2:
                x, y = args[:2]
            else:
                x, y = kw.get('x'), kw.get('y')
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                raise ValueError('WPS_ABSOLUTE_POINTER_REQUIRED')
            if any(n['x'] <= x < n['x']+n['w'] and n['y'] <= y < n['y']+n['h'] for n in protected):
                raise ValueError('WPS_APPLICATION_CONTROL_FORBIDDEN')
            if str(target.get('source') or '').startswith('accessibility'):
                if any(n['role'] == 'document-web' for n in controls):
                    raise ValueError('WPS_BACKGROUND_WEB_TREE_FORBIDDEN')
                hits = [n for n in controls if norm(n['label']) == label
                        and norm(n['role']) == norm(target.get('role'))
                        and n['x'] <= x < n['x']+n['w'] and n['y'] <= y < n['y']+n['h']]
                if len(hits) != 1:
                    raise ValueError('WPS_ACCESSIBILITY_TARGET_UNPROVEN')


def install(shim: Any, local: Any) -> None:
    if os.environ.get('ARBM_STRICT_WPS') != '1':
        raise ValueError('WPS_STRICT_MODE_REQUIRED')
    if os.environ.get('ZERO_SPEND_MODE') != 'HARD':
        raise ValueError('WPS_ZERO_SPEND_HARD_REQUIRED')
    if getattr(shim, '_strict_wps_installed', False):
        return
    original_call, original_ground = shim.call_mesh, shim.ground_action
    original_candidates = local._selector_candidates
    context = threading.local()

    def candidates(body: dict[str, Any], limit: int = 18) -> list[dict[str, Any]]:
        observation = str(body.get('observation') or '')
        if norm(body.get('active_application')) != APP:
            raise ValueError('LOCAL_SELECTOR_WPS_CONTEXT_REQUIRED')
        allowed = []
        for item in original_candidates(body, limit=limit):
            try:
                validate_action(item['action'], observation, canonical=True)
            except (ValueError, SyntaxError, TypeError):
                continue
            allowed.append(item)
        if not allowed:
            raise ValueError('LOCAL_SELECTOR_WPS_NO_CANDIDATES')
        return allowed

    def grounded(value: Any, active: str, observation: str, *args: Any, **kwargs: Any) -> dict[str, Any]:
        action = original_ground(value, active, observation, *args, **kwargs)
        raw = getattr(context, 'raw', observation)
        if observed_app(raw) != APP:
            raise ValueError('WPS_FOREGROUND_REQUIRED')
        validate_action(action, observation, canonical=True)
        shim.log_event({'status': 'STRICT_WPS_ACTION_ADMITTED', 'active_application': 'WPS Presentation',
                        'observation_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                        'command_sha256': hashlib.sha256(str(action.get('command') or '').encode()).hexdigest()})
        return action

    def call(messages: list[dict[str, Any]]) -> str:
        if shim.STATE.get('terminal'):
            return 'FAIL'
        raw, image = shim.latest_observation(messages)
        if not image:
            return shim.terminal('WPS_SCREENSHOT_REQUIRED')
        try:
            active = observed_app(raw)
        except ValueError as exc:
            return shim.terminal(str(exc))
        if active != APP:
            if time.monotonic()-shim.STARTED >= shim.MAX_TASK_SECONDS or shim.STATE['step'] >= shim.MAX_STEPS:
                return shim.terminal('WPS_FOCUS_BUDGET_EXHAUSTED')
            try:
                count = int(shim.STATE.get('wps_focus_attempts', 0))
                candidate = focus_recovery(raw, count)
                action = original_ground(candidate, active, raw, [])
            except ValueError as exc:
                return shim.terminal(str(exc))
            command = action['command']
            shim.STATE['step'] += 1
            shim.STATE['wps_focus_attempts'] = count+1
            shim.VERIFIER.observe(raw, image)
            shim.STATE['previous'] = command
            shim.STATE['executed'] += 1
            shim.STATE['history'].append({'command': command, 'source': 'wps-focus-recovery'})
            shim.STATE['history'] = shim.STATE['history'][-12:]
            shim.VERIFIER.issued(command)
            shim.log_event({'status': 'WPS_FOCUS_RECOVERY_ISSUED', 'attempt': count+1,
                            'command_sha256': hashlib.sha256(command.encode()).hexdigest(),
                            'observation_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                            'activation_verified': False})
            shim.log_event({'status': 'ACTION_ISSUED', 'source': 'wps-focus-recovery', 'command': command})
            return '```python\n'+command+'\n```'
        context.raw = raw
        try:
            shim.log_event({'status': 'WPS_FOCUS_OBSERVED', 'active_application': 'WPS Presentation',
                            'observation_sha256': hashlib.sha256(raw.encode()).hexdigest()})
            return original_call(messages)
        finally:
            context.raw = ''

    local._selector_candidates = candidates
    shim.ground_action = grounded
    shim.call_mesh = call
    shim._strict_wps_installed = True


def audit(path: Path) -> dict[str, Any]:
    allowed: set[tuple[Any, str]] = set()
    recoveries = admitted = issued = 0
    observed = False
    for line in path.read_text().splitlines():
        event = json.loads(line)
        status = event.get('status')
        if status == 'WPS_FOCUS_OBSERVED':
            observed = event.get('active_application') == 'WPS Presentation'
        if status in {'STRICT_WPS_ACTION_ADMITTED', 'WPS_FOCUS_RECOVERY_ISSUED'}:
            digest = event.get('observation_sha256', '')
            if not re.fullmatch('[a-f0-9]{64}', digest):
                raise ValueError('WPS_OBSERVATION_PROOF_MISSING')
            allowed.add((event.get('step'), event.get('command_sha256')))
            recoveries += status == 'WPS_FOCUS_RECOVERY_ISSUED'
            admitted += status == 'STRICT_WPS_ACTION_ADMITTED'
        if status == 'ACTION_ISSUED':
            digest = hashlib.sha256(event.get('command', '').encode()).hexdigest()
            if (event.get('step'), digest) not in allowed:
                raise ValueError('WPS_ACTION_WITHOUT_ADMISSION')
            issued += 1
    if not observed or not admitted or not issued or recoveries > MAX_FOCUS_ATTEMPTS:
        raise ValueError('WPS_TRACE_INCOMPLETE')
    return {'status': 'STRICT_WPS_TRACE_PASS', 'focus_recoveries': recoveries,
            'admissions': admitted, 'issued': issued, 'official_score_claimed': False}


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == '--audit':
        print(json.dumps(audit(Path(sys.argv[2])), sort_keys=True))
        return
    if len(sys.argv) != 1:
        raise SystemExit('usage: osworld_wps_focus.py [--audit shim.jsonl]')
    import osworld_free_mesh_shim as shim
    import osworld_local_vlm as local
    install(shim, local)
    threading.Thread(target=shim.heartbeat, daemon=True).start()
    if os.environ.get('ARBM_ENABLE_LOCAL_VLM') == '1':
        threading.Thread(target=shim.warm_runtime, daemon=True, name='arbm-wps-local-vlm-warmup').start()
    shim.ThreadingHTTPServer(('127.0.0.1', 8088), shim.Handler).serve_forever()


if __name__ == '__main__':
    main()
