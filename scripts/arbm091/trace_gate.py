"""Validate trusted, read-only UI observations; a UI change is not task success."""
from __future__ import annotations
import ast
import hashlib
import json
import io
from pathlib import Path

DECK = 'Operating_Committee_Rebaseline_Draft.pptx'
WORKBOOK = 'Reforecast_Model_H2.xlsx'
ALLOWED_LAUNCHERS = {'google chrome', 'wps presentation', 'wps 2019', 'wps office',
                     'wps spreadsheets', DECK.lower(), WORKBOOK.lower()}
POINTERS = {'click', 'doubleClick', 'rightClick', 'moveTo', 'mouseDown', 'mouseUp', 'dragTo'}
NON_EDITING = {'moveTo', 'sleep', 'keyDown', 'keyUp'}
WPS_TRANSIENT_TITLES = {'system check', 'wps office', 'set wps office as your default office software',
                        'presentation', 'replace', 'find', 'find and replace', 'find & replace'}

TASK091_CANONICAL_SCREEN = [0, 0, 1920, 1080]
TASK091_CANONICAL_WINDOW = [70, 27, 1850, 1053]
TASK091_CANONICAL_SLIDE_VIEWPORT = [443, 194, 1413, 795]


def _task091_shape_boxes(snapshot: dict) -> list[tuple[int,int,int,int]]:
    deck_file=snapshot.get('deck_file', {}) if isinstance(snapshot, dict) else {}
    slide_size=deck_file.get('slide_size', {}) if isinstance(deck_file, dict) else {}
    sw=int(slide_size.get('w') or 0) if isinstance(slide_size, dict) else 0
    sh=int(slide_size.get('h') or 0) if isinstance(slide_size, dict) else 0
    if sw <= 0 or sh <= 0:
        return []
    table=snapshot.get('deck_slide_shapes', {}) if isinstance(snapshot, dict) else {}
    if not isinstance(table, dict):
        return []
    active_slide=snapshot.get('active_slide')
    if type(active_slide) is not int or active_slide <= 0:
        return []
    rows=table.get(str(active_slide), [])
    if not isinstance(rows, list):
        return []
    vx,vy,vw,vh=TASK091_CANONICAL_SLIDE_VIEWPORT
    boxes=[]
    for row in rows:
            if not isinstance(row, dict) or not str(row.get('text') or '').strip():
                continue
            geometry=row.get('geometry', {})
            if not isinstance(geometry, dict):
                continue
            gx=int(geometry.get('x') or 0); gy=int(geometry.get('y') or 0)
            gw=int(geometry.get('w') or 0); gh=int(geometry.get('h') or 0)
            if gx < 0 or gy < 0 or gw <= 0 or gh <= 0:
                continue
            left=round(vx + (gx/sw)*vw)
            top=round(vy + (gy/sh)*vh)
            right=round(vx + ((gx+gw)/sw)*vw)
            bottom=round(vy + ((gy+gh)/sh)*vh)
            left=max(vx,int(left)); top=max(vy,int(top))
            right=min(vx+vw,int(right)); bottom=min(vy+vh,int(bottom))
            if right-left >= 2 and bottom-top >= 2:
                boxes.append((left,top,right-left,bottom-top))
    return boxes

def _task091_shape_points(snapshot: dict) -> set[tuple[int, int]]:
    points=set()
    for x,y,w,h in _task091_shape_boxes(snapshot):
        points.add((x+w//2,y+h//2))
    return points

def _task091_point_inside_unique_text_shape(snapshot: dict, point: tuple[int,int]) -> bool:
    x,y=point
    hits=0
    for bx,by,bw,bh in _task091_shape_boxes(snapshot):
        if bx <= x < bx+bw and by <= y < by+bh:
            hits += 1
            if hits > 1:
                return False
    return hits == 1


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _is_wps_class(klass: str) -> bool:
    value=str(klass or '').casefold()
    return any(x in value for x in ('wps', 'wpp', 'kingsoft'))


def is_authorized_wps_transient(window: dict) -> bool:
    if not isinstance(window, dict):
        return False
    title=str(window.get('title', '')).strip().casefold()
    owner=str(window.get('owner_title', '')).strip().casefold()
    klass=str(window.get('wm_class', '')).strip().casefold()
    deck_owned=(_is_wps_class(klass)
                and DECK.casefold() in owner
                and title in {'system check','wps office','set wps office as your default office software'})
    bootstrap_root=(title == 'wps office'
                    and owner == ''
                    and klass == 'wpsoffice wpsoffice'
                    and window.get('bbox') == TASK091_CANONICAL_WINDOW)
    return deck_owned or bootstrap_root


def _is_legacy_wps_modal(window: dict) -> bool:
    title=str(window.get('title', '')).strip().casefold()
    owner=str(window.get('owner_title', '')).strip().casefold()
    klass_tokens=set(str(window.get('wm_class','')).casefold().replace('.',' ').replace('-',' ').split())
    legacy=(title in {'presentation','replace','find','find and replace','find & replace'}
            or owner in {'presentation','replace','find','find and replace','find & replace'}
            or 'replace' in owner or 'find' in owner)
    return 'wpp' in klass_tokens and legacy


def classify(window: dict) -> str:
    require(isinstance(window, dict), 'WINDOW_OBJECT_REQUIRED')
    require(type(window.get('pid')) is int and window['pid'] > 0, 'WINDOW_PID_UNPROVEN')
    require(type(window.get('id')) is int and window['id'] > 0, 'WINDOW_ID_UNPROVEN')
    title = str(window.get('title', ''))
    owner = str(window.get('owner_title', ''))
    klass = str(window.get('wm_class', '')).casefold()
    titles = (title + ' ' + owner).casefold()
    if is_authorized_wps_transient(window):
        return 'wps-transient'
    if DECK.casefold() in title.casefold() and _is_wps_class(klass):
        return 'wps-presentation'
    if _is_legacy_wps_modal(window):
        return 'wps-presentation'
    if WORKBOOK.casefold() in titles and any(x in klass for x in ('wps', 'et', 'kingsoft', 'libreoffice', 'soffice')):
        return 'reference-workbook'
    if 'mailhub' in titles and any(x in klass for x in ('chrome', 'chromium')):
        return 'reference-memo'
    return 'unapproved'

def parse_atom(command: str):
    tree = ast.parse(command)
    require(len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr), 'ATOMIC_GUI_CALL_REQUIRED')
    call = tree.body[0].value
    require(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
            and isinstance(call.func.value, ast.Name) and call.func.value.id == 'pyautogui',
            'GUI_CALL_REQUIRED')
    args = [ast.literal_eval(arg) for arg in call.args]
    kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in call.keywords}
    require(None not in kwargs, 'EXPANDED_ARGUMENTS_FORBIDDEN')
    return call.func.attr, args, kwargs


def pointer(command: str):
    name, args, kwargs = parse_atom(command)
    if name not in POINTERS:
        return None
    if len(args) >= 2:
        x, y = args[:2]
    elif 'x' in kwargs and 'y' in kwargs:
        x, y = kwargs['x'], kwargs['y']
    else:
        raise ValueError('EXPLICIT_POINTER_COORDINATES_REQUIRED')
    require(type(x) in (int, float) and type(y) in (int, float), 'POINTER_COORDINATES_INVALID')
    require(float(x).is_integer() and float(y).is_integer(), 'PIXEL_COORDINATES_REQUIRED')
    return int(x), int(y)


def inside(point: tuple[int, int], box: list[int]) -> bool:
    require(isinstance(box, list) and len(box) == 4 and all(type(v) is int for v in box),
            'BOUNDING_BOX_INVALID')
    x, y, w, h = box
    return w > 0 and h > 0 and x <= point[0] < x + w and y <= point[1] < y + h


def _is_press(name, args, key):
    return name == 'press' and bool(args) and str(args[0]).casefold() == key


def preflight(command: str, snapshot: dict) -> str:
    require(snapshot.get('stable') is True, 'FOREGROUND_UNSTABLE')
    window = snapshot.get('window', {})
    app = classify(window)
    name, args, _ = parse_atom(command)
    point = pointer(command)

    if app == 'wps-transient':
        title=str(window.get('title', '')).strip().casefold()
        if name == 'hotkey' and set(args) in ({'alt','tab'},{'alt','f4'}):
            raise ValueError('WPS_TRANSIENT_SWITCH_OR_CLOSE_SHORTCUT_FORBIDDEN')
        if title == 'system check':
            require(name == 'sleep' or _is_press(name,args,'tab') or _is_press(name,args,'space')
                    or (name == 'click' and point is not None),
                    'SYSTEM_CHECK_ACTION_FORBIDDEN')
        elif title in ('wps office','set wps office as your default office software'):
            require(name == 'sleep' or _is_press(name,args,'esc'),
                    'DEFAULT_OFFICE_ACTION_FORBIDDEN')

    if point is not None:
        target = snapshot.get('target')
        deck_spatial = (target is None and app == 'wps-presentation'
                        and name in ('click','doubleClick')
                        and isinstance(snapshot.get('deck_slide_text'), dict)
                        and bool(snapshot.get('deck_slide_text')))
        if deck_spatial:
            require(snapshot.get('screen') == TASK091_CANONICAL_SCREEN,
                    'TASK091_CANONICAL_SCREEN_UNPROVEN')
            require(window.get('bbox') == TASK091_CANONICAL_WINDOW,
                    'TASK091_CANONICAL_DECK_GEOMETRY_UNPROVEN')
            require(isinstance(snapshot.get('deck_file'), dict)
                    and str(snapshot['deck_file'].get('path','')) ==
                    '/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx'
                    and len(str(snapshot['deck_file'].get('sha256',''))) == 64,
                    'TASK091_TARGET_DECK_FILE_UNPROVEN')
            require(type(snapshot.get('active_slide')) is int
                    and snapshot.get('active_slide') > 0,
                    'TASK091_ACTIVE_SLIDE_UNPROVEN')
            require(str(snapshot.get('active_slide')) in snapshot.get('deck_slide_shapes', {}),
                    'TASK091_ACTIVE_SLIDE_SHAPES_UNPROVEN')
            require(_task091_point_inside_unique_text_shape(snapshot, point),
                    'TASK091_SHAPE_POINT_UNPROVEN')
            require(inside(point, snapshot.get('screen')), 'POINTER_OUTSIDE_SCREEN')
            require(inside(point, window.get('bbox')), 'POINTER_OUTSIDE_FOREGROUND')
            return 'wps-content'
        require(isinstance(target, dict), 'UI_TARGET_UNAVAILABLE')
        require(target.get('showing') is True and target.get('enabled') is True,
                'UI_TARGET_NOT_INTERACTIVE')
        require(inside(point, target.get('bbox')), 'POINTER_OUTSIDE_TARGET')
        require(inside(point, snapshot.get('screen')), 'POINTER_OUTSIDE_SCREEN')
        label = str(target.get('label', '')).strip().casefold()
        launcher = (target.get('role') in ('push button', 'push-button', 'button', 'icon')
                    and label in ALLOWED_LAUNCHERS
                    and str(target.get('application', '')).casefold() in
                    ('gnome-shell', 'gnome shell', 'unity', 'ubuntu dock'))
        if launcher and name in ('click', 'doubleClick'):
            return 'application-switch'
        require(app != 'unapproved', 'UNAPPROVED_APPLICATION')
        require(type(target.get('pid')) is int and target['pid'] == window['pid'],
                'BACKGROUND_TARGET_PID_MISMATCH')
        require(inside(point, window.get('bbox')), 'POINTER_OUTSIDE_FOREGROUND')
        require(snapshot.get('hit_owner_id') == window['id'], 'POINTER_OCCLUDED_OR_FOREIGN_WINDOW')
        if app == 'wps-transient' and str(window.get('title','')).strip().casefold() == 'system check':
            require(name == 'click', 'SYSTEM_CHECK_POINTER_ACTION_FORBIDDEN')
            require(str(target.get('label','')).strip().casefold() == 'close'
                    and str(target.get('role','')).strip().casefold() in ('push button','push-button','button'),
                    'SYSTEM_CHECK_CLOSE_TARGET_UNPROVEN')
    elif name == 'hotkey' and set(args) == {'alt', 'tab'}:
        require(app != 'wps-transient', 'WPS_TRANSIENT_APP_SWITCH_FORBIDDEN')
        return 'application-switch'
    elif name == 'sleep':
        # A bounded sleep is a non-interacting timing no-op. Preserve the
        # stronger WPS bootstrap classification when that exact transient is
        # proven; otherwise allow waiting only outside ambiguous WPS windows.
        require(len(args) == 1 and type(args[0]) in (int, float), 'NEUTRAL_WAIT_DURATION_REQUIRED')
        require(0 <= float(args[0]) <= 2.0, 'NEUTRAL_WAIT_DURATION_UNBOUNDED')
        if app == 'wps-transient':
            return 'wps-transient'
        if app == 'unapproved':
            title=str(window.get('title', '')).strip().casefold()
            require(title not in {'wps office','set wps office as your default office software'}
                    and not _is_wps_class(window.get('wm_class','')),
                    'UNAPPROVED_APPLICATION')
            return 'neutral-wait'
    else:
        require(app != 'unapproved', 'UNAPPROVED_APPLICATION')
    return 'wps-transient' if app == 'wps-transient' else ('wps-content' if app == 'wps-presentation' else 'reference')


def postflight(command: str, before: dict, after: dict) -> str:
    require(after.get('stable') is True, 'FOREGROUND_UNSTABLE')
    before_window=before.get('window', {})
    after_window=after.get('window', {})
    before_app=classify(before_window)
    after_app=classify(after_window)
    name,args,_=parse_atom(command)
    if before_app == 'wps-transient':
        require(after_app in ('wps-transient','wps-presentation'),
                'WPS_TRANSIENT_CLOSE_UNPROVEN')
        before_title=str(before_window.get('title', '')).strip().casefold()
        before_owner=str(before_window.get('owner_title', '')).strip().casefold()
        after_title=str(after_window.get('title', '')).strip().casefold()
        if after_app == 'wps-transient':
            require(after_window.get('pid') == before_window.get('pid'),
                    'WPS_TRANSIENT_CLOSE_UNPROVEN')
        else:
            require(DECK.casefold() in before_owner and DECK.casefold() in after_title
                    and _is_wps_class(after_window.get('wm_class','')),
                    'WPS_TRANSIENT_OWNER_HANDOFF_UNPROVEN')
        if before_title == 'system check' and _is_press(name,args,'tab'):
            require(after_app == 'wps-transient' and after_title == 'system check',
                    'WPS_TRANSIENT_CLOSE_UNPROVEN')
        if before_title == 'system check' and _is_press(name,args,'space'):
            require((after_app == 'wps-transient' and after_title == 'system check')
                    or after_app == 'wps-presentation',
                    'WPS_TRANSIENT_CLOSE_UNPROVEN')
        if before_title == 'system check' and name == 'click':
            require(after_title != 'system check' and after_app == 'wps-presentation',
                    'WPS_TRANSIENT_CLOSE_UNPROVEN')
        if before_title in ('wps office','set wps office as your default office software') and _is_press(name,args,'esc'):
            require(after_title != before_title,'WPS_TRANSIENT_CLOSE_UNPROVEN')
    return after_app

def is_save(command: str) -> bool:
    name, args, _ = parse_atom(command)
    return name == 'hotkey' and set(args) == {'ctrl', 's'}


def read_snapshot(root: Path, ref: dict) -> dict:
    require(isinstance(ref, dict), 'SNAPSHOT_REFERENCE_REQUIRED')
    def read_safe(name):
        require(isinstance(name, str) and name, 'EVIDENCE_PATH_REQUIRED')
        path = root / name
        require(not path.is_symlink() and path.resolve().is_relative_to(root.resolve()),
                'UNSAFE_EVIDENCE_PATH')
        require(path.is_file(), 'MISSING_EVIDENCE:' + name)
        return path.read_bytes()
    raw = read_safe(ref.get('metadata'))
    require(hashlib.sha256(raw).hexdigest() == ref.get('metadata_sha256'), 'SNAPSHOT_HASH_MISMATCH')
    obj = json.loads(raw)
    png = read_safe(ref.get('screenshot'))
    require(png.startswith(b'\x89PNG\r\n\x1a\n'), 'SCREENSHOT_NOT_PNG')
    require(hashlib.sha256(png).hexdigest() == ref.get('screenshot_sha256'), 'SCREENSHOT_HASH_MISMATCH')
    from PIL import Image
    with Image.open(io.BytesIO(png)) as image:
        require(image.format == 'PNG' and obj.get('screen') == [0, 0, image.width, image.height],
                'SCREENSHOT_GEOMETRY_MISMATCH')
        image.verify()
    return obj


def verify_trace(root: Path, sha: str, run_id: str, run_attempt: str) -> dict:
    trace = root / 'wps-trace.jsonl'
    require(trace.is_file() and not trace.is_symlink(), 'WPS_TRACE_MISSING')
    raw = trace.read_bytes()
    require(bool(raw) and raw.endswith(b'\n'), 'TRACE_EMPTY_OR_TRUNCATED')
    previous = '0' * 64
    steps = set()
    wps = edits = saves = switches = transients = 0
    for ordinal, line in enumerate(raw.decode().splitlines(), 1):
        row = json.loads(line)
        event_hash = row.pop('event_sha256', None)
        require(row.get('previous_sha256') == previous and digest(row) == event_hash,
                'TRACE_CHAIN_INVALID')
        previous = event_hash
        require(row.get('ordinal') == ordinal, 'TRACE_ORDER_INVALID')
        require(row.get('candidate_sha') == sha and row.get('task_id') == '091'
                and str(row.get('run_id')) == run_id and str(row.get('run_attempt')) == run_attempt,
                'TRACE_PROVENANCE_MISMATCH')
        require(row.get('kind') == 'action' and row.get('status') == 'executed',
                'TRACE_ACTION_NOT_EXECUTED')
        require(type(row.get('returncode')) is int and row['returncode'] == 0,
                'GUEST_ACTION_FAILED')
        command = row.get('command')
        require(isinstance(command, str) and command, 'TRACE_COMMAND_REQUIRED')
        require(hashlib.sha256(command.encode()).hexdigest() == row.get('command_sha256'),
                'TRACE_COMMAND_HASH_MISMATCH')
        key = (row.get('step'), row.get('substep'))
        require(key not in steps and type(key[0]) is int and key[0] > 0
                and type(key[1]) is int and key[1] > 0, 'DUPLICATE_OR_INVALID_STEP')
        steps.add(key)
        before = read_snapshot(root, row.get('before'))
        after = read_snapshot(root, row.get('after'))
        require(after.get('captured_monotonic_ns', 0) > before.get('captured_monotonic_ns', 0),
                'STALE_OR_REORDERED_FRAME')
        scope = preflight(command, before)
        require(scope == row.get('scope'), 'TRACE_SCOPE_MISMATCH')
        after_app = postflight(command, before, after)
        if scope == 'application-switch':
            switches += 1
            continue
        if scope == 'neutral-wait':
            name, args, _ = parse_atom(command)
            require(name == 'sleep' and len(args) == 1 and 0 <= float(args[0]) <= 2.0,
                    'NEUTRAL_WAIT_SCOPE_INVALID')
            continue
        require(after_app != 'unapproved', 'POST_ACTION_APP_DRIFT')
        if scope == 'wps-transient':
            wps += 1
            transients += 1
            continue
        if scope == 'wps-content':
            wps += 1
            require(after_app in ('wps-presentation','wps-transient'), 'WPS_CONTEXT_LOST')
            if is_save(command):
                saves += 1
            elif parse_atom(command)[0] not in NON_EDITING:
                if row['before']['screenshot_sha256'] != row['after']['screenshot_sha256']:
                    edits += 1
    require(wps > 0, 'WPS_ACTIONS_UNPROVEN')
    require(edits > 0, 'WPS_UI_EFFECT_UNPROVEN')
    require(saves > 0, 'AGENT_WPS_SAVE_UNPROVEN')
    return {'wps_actions': wps, 'wps_ui_changes': edits, 'agent_save_actions': saves,
            'application_switches': switches, 'wps_transient_actions': transients, 'trace_tail_sha256': previous,
            'note': 'UI effects do not establish semantic task success; official score is separately required.'}
