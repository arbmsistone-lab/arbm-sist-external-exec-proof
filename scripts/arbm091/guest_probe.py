"""Read-only X11/AT-SPI probe. Executed inside the isolated benchmark VM only.

The caller sets POINT to a JSON-compatible pixel pair or None. No task files,
network endpoints, evaluator internals or reference answers are read here.
"""
import base64
import io
import json
import time
from Xlib import X, display
import pyautogui


def capture(point):
    connection = display.Display()
    root = connection.screen().root

    def prop(window, name):
        value = window.get_full_property(connection.intern_atom(name), X.AnyPropertyType)
        return value.value if value is not None else None

    def integer(window, name):
        value = prop(window, name)
        return int(value[0]) if value is not None and len(value) else 0

    def title(window):
        value = prop(window, '_NET_WM_NAME')
        if value is not None:
            return value.decode('utf-8', 'replace') if isinstance(value, bytes) else str(value)
        return str(window.get_wm_name() or '')

    def box(window):
        geometry = window.get_geometry()
        translated = root.translate_coords(window, 0, 0)
        return [int(translated.x), int(translated.y), int(geometry.width), int(geometry.height)]

    def contains(rect, candidate=None):
        candidate = point if candidate is None else candidate
        if candidate is None:
            return False
        x, y, w, h = rect
        return w > 0 and h > 0 and x <= candidate[0] < x + w and y <= candidate[1] < y + h

    def window_info():
        window_id = integer(root, '_NET_ACTIVE_WINDOW')
        if not window_id:
            raise RuntimeError('X11_ACTIVE_WINDOW_MISSING')
        window = connection.create_resource_object('window', window_id)
        owner = window.get_wm_transient_for()
        return {'id': window_id, 'pid': integer(window, '_NET_WM_PID'),
                'title': title(window), 'wm_class': ' '.join(window.get_wm_class() or ()),
                'owner_title': title(owner) if owner else '', 'bbox': box(window)}

    def hit_owner():
        if point is None:
            return 0, 0
        current = root
        chain = []
        for _ in range(32):
            child_hit = None
            for child in reversed(current.query_tree().children[-256:]):
                try:
                    if child.get_attributes().map_state == X.IsViewable and contains(box(child)):
                        child_hit = child
                        break
                except Exception:
                    continue
            if child_hit is None:
                break
            chain.append(child_hit)
            current = child_hit
        for window in reversed(chain):
            pid = integer(window, '_NET_WM_PID')
            if pid:
                return int(window.id), int(pid)
        return 0, 0

    before = window_info()
    target = None
    controls = []
    focused_control = None

    import pyatspi
    candidates = []
    remaining = [4096]
    active_rect = before['bbox']

    def in_active_window(rect):
        if not isinstance(rect, list) or len(rect) != 4:
            return False
        x, y, w, h = rect
        if w <= 0 or h <= 0:
            return False
        center = (x + w // 2, y + h // 2)
        return contains(active_rect, center)

    def visit(node, application, pid, depth):
        if depth > 32 or remaining[0] <= 0:
            return
        remaining[0] -= 1
        try:
            state = node.getState()
            if not state.contains(pyatspi.STATE_SHOWING):
                return
            ext = node.queryComponent().getExtents(pyatspi.DESKTOP_COORDS)
            rect = [int(ext.x), int(ext.y), int(ext.width), int(ext.height)]
            role = str(node.getRoleName()).casefold()
            label = str(node.name or '')
            enabled = bool(state.contains(pyatspi.STATE_ENABLED))
            focused = bool(state.contains(pyatspi.STATE_FOCUSED))
            item = {'label': label, 'role': role, 'pid': pid,
                    'application': application, 'bbox': rect,
                    'showing': True, 'enabled': enabled,
                    'focused': focused, 'depth': depth}
            if label and role not in ('application', 'frame', 'window'):
                if pid == before['pid'] and in_active_window(rect):
                    controls.append(item)
                if point is not None and contains(rect):
                    candidates.append(item)
            for child in node:
                visit(child, application, pid, depth + 1)
        except Exception:
            return

    desktop = pyatspi.Registry.getDesktop(0)
    for application in desktop:
        getter = getattr(application, 'get_process_id', None) or getattr(application, 'getProcessId', None)
        pid = int(getter()) if getter else 0
        name = str(application.name or '')
        if pid != before['pid'] and name.casefold() not in ('gnome-shell', 'gnome shell', 'unity', 'ubuntu dock'):
            continue
        for child in application:
            visit(child, name, pid, 0)

    if remaining[0] <= 0:
        raise RuntimeError('ACCESSIBILITY_INSPECTION_LIMIT')

    unique = {}
    for item in controls:
        key = (item['pid'], item['role'], item['label'], tuple(item['bbox']))
        current = unique.get(key)
        if current is None or (item['focused'] and not current['focused']) or item['depth'] > current['depth']:
            unique[key] = item
    controls = sorted(unique.values(), key=lambda value: (
        not value['focused'], -value['depth'], value['bbox'][1], value['bbox'][0],
        value['bbox'][2] * value['bbox'][3]))[:128]
    focused = [value for value in controls if value['focused'] and value['enabled']]
    if len(focused) == 1:
        focused_control = focused[0]

    candidates.sort(key=lambda value: (-value['depth'], value['bbox'][2] * value['bbox'][3]))
    if candidates:
        first = candidates[0]
        tied = [value for value in candidates if value['depth'] == first['depth']
                and value['bbox'][2] * value['bbox'][3] == first['bbox'][2] * first['bbox'][3]]
        if len(tied) != 1:
            raise RuntimeError('ACCESSIBILITY_TARGET_AMBIGUOUS')
        target = first

    image = pyautogui.screenshot()
    output = io.BytesIO()
    image.save(output, format='PNG')
    owner_id, owner_pid = hit_owner()
    after = window_info()
    result = {'window': after, 'target': target, 'controls': controls,
              'focused_control': focused_control, 'hit_owner_id': owner_id,
              'hit_owner_pid': owner_pid, 'screen': [0, 0, image.width, image.height],
              'stable': before == after, 'captured_monotonic_ns': time.monotonic_ns(),
              'screenshot_base64': base64.b64encode(output.getvalue()).decode('ascii')}
    connection.close()
    return result


print(json.dumps(capture(POINT), sort_keys=True))
