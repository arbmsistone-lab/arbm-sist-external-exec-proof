"""Read-only X11/AT-SPI and target-deck verifier inside the benchmark VM.

The caller sets POINT to a JSON-compatible pixel pair or None. The only file
content read is the exact active target deck on the guest Desktop, solely to
verify already-issued GUI edits. Evaluator internals, reference answers and
network endpoints are never read.
"""
import base64
import io
import json
import time
import os
import zipfile
import xml.etree.ElementTree as ET
import hashlib
from Xlib import X, display
import pyautogui


def _semantic_slide_text(shapes):
    """Flatten parsed shape/cell text without splitting DrawingML runs."""
    parts=[]
    for row in shapes if isinstance(shapes,list) else []:
        if not isinstance(row,dict):
            continue
        value=' '.join(str(row.get('text') or '').split())
        if value:
            parts.append(value)
    return ' '.join(parts)


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

    def deck_slide_content(window):
        title_value = str(window.get('title', ''))
        path = '/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx'
        if 'Operating_Committee_Rebaseline_Draft.pptx' not in title_value or not os.path.isfile(path):
            return {}, {}, {}, {}
        text_result = {}
        run_result = {}
        shape_result = {}
        metadata = {}
        try:
            raw = open(path, 'rb').read()
            stat = os.stat(path)
            metadata = {'path': path, 'size': int(stat.st_size),
                        'mtime_ns': int(stat.st_mtime_ns),
                        'sha256': hashlib.sha256(raw).hexdigest()}
            with zipfile.ZipFile(io.BytesIO(raw), 'r') as archive:
                if 'ppt/presentation.xml' in archive.namelist():
                    presentation = ET.fromstring(archive.read('ppt/presentation.xml'))
                    slide_size = next((node for node in presentation.iter()
                                       if node.tag.endswith('}sldSz')), None)
                    if slide_size is not None:
                        metadata['slide_size'] = {
                            'w': int(slide_size.attrib.get('cx', '0')),
                            'h': int(slide_size.attrib.get('cy', '0')),
                        }
                names = [name for name in archive.namelist()
                         if name.startswith('ppt/slides/slide') and name.endswith('.xml')]
                for name in names:
                    base = name.rsplit('/', 1)[-1]
                    number = base[len('slide'):-len('.xml')]
                    if not number.isdigit():
                        continue
                    root_xml = ET.fromstring(archive.read(name))
                    parts = []
                    shapes = []
                    for node in root_xml.iter():
                        if node.tag.endswith('}t') and node.text is not None:
                            value = ' '.join(str(node.text).split())
                            if value:
                                parts.append(value)
                    for shape in root_xml.iter():
                        if not shape.tag.endswith('}sp'):
                            continue
                        c_nv_pr = next((node for node in shape.iter()
                                      if node.tag.endswith('}cNvPr')), None)
                        shape_id = int(c_nv_pr.attrib.get('id', '0')) if c_nv_pr is not None else 0
                        shape_name = str(c_nv_pr.attrib.get('name', '')) if c_nv_pr is not None else ''
                        paragraphs = []
                        for paragraph in shape.iter():
                            if not paragraph.tag.endswith('}p'):
                                continue
                            chunks = []
                            for text_node in paragraph.iter():
                                if text_node.tag.endswith('}t') and text_node.text is not None:
                                    chunks.append(str(text_node.text))
                                elif text_node.tag.endswith('}br'):
                                    chunks.append('\n')
                            if chunks:
                                paragraphs.append(''.join(chunks))
                        shape_text = '\n'.join(paragraphs)
                        if not shape_text:
                            continue
                        off = ext = None
                        sp_pr = next((node for node in shape
                                     if node.tag.endswith('}spPr')), None)
                        if sp_pr is not None:
                            xfrm = next((node for node in sp_pr.iter()
                                         if node.tag.endswith('}xfrm')), None)
                            if xfrm is not None:
                                off = next((node for node in xfrm
                                            if node.tag.endswith('}off')), None)
                                ext = next((node for node in xfrm
                                            if node.tag.endswith('}ext')), None)
                        geometry = {}
                        if off is not None and ext is not None:
                            geometry = {
                                'x': int(off.attrib.get('x', '0')),
                                'y': int(off.attrib.get('y', '0')),
                                'w': int(ext.attrib.get('cx', '0')),
                                'h': int(ext.attrib.get('cy', '0')),
                            }
                        font_sizes=[]
                        for node in shape.iter():
                            if node.tag.endswith('}rPr') or node.tag.endswith('}defRPr') or node.tag.endswith('}endParaRPr'):
                                raw_size=node.attrib.get('sz')
                                if raw_size is not None:
                                    try:
                                        font_sizes.append(int(raw_size))
                                    except ValueError:
                                        pass
                        fill_rgb=''
                        if sp_pr is not None:
                            solid_fill=next((node for node in sp_pr.iter()
                                             if node.tag.endswith('}solidFill')),None)
                            if solid_fill is not None:
                                rgb=next((node for node in solid_fill.iter()
                                          if node.tag.endswith('}srgbClr')),None)
                                if rgb is not None:
                                    fill_rgb=str(rgb.attrib.get('val','')).upper()
                        shapes.append({'id': shape_id, 'name': shape_name,
                                       'text': shape_text, 'paragraphs': paragraphs,
                                       'geometry': geometry, 'kind':'shape',
                                       'font_sizes':font_sizes,'fill_rgb':fill_rgb})
                    for frame in root_xml.iter():
                        if not frame.tag.endswith('}graphicFrame'):
                            continue
                        c_nv_pr = next((node for node in frame.iter()
                                      if node.tag.endswith('}cNvPr')), None)
                        frame_id = int(c_nv_pr.attrib.get('id', '0')) if c_nv_pr is not None else 0
                        frame_name = str(c_nv_pr.attrib.get('name', '')) if c_nv_pr is not None else ''
                        xfrm = next((node for node in frame
                                     if node.tag.endswith('}xfrm')), None)
                        if xfrm is None:
                            continue
                        off = next((node for node in xfrm if node.tag.endswith('}off')), None)
                        ext = next((node for node in xfrm if node.tag.endswith('}ext')), None)
                        table = next((node for node in frame.iter()
                                      if node.tag.endswith('}tbl')), None)
                        if table is None or off is None or ext is None:
                            continue
                        fx=int(off.attrib.get('x','0')); fy=int(off.attrib.get('y','0'))
                        fw=int(ext.attrib.get('cx','0')); fh=int(ext.attrib.get('cy','0'))
                        rows=[node for node in table if node.tag.endswith('}tr')]
                        grid=next((node for node in table if node.tag.endswith('}tblGrid')),None)
                        cols=[int(node.attrib.get('w','0')) for node in grid] if grid is not None else []
                        row_heights=[int(row.attrib.get('h','0')) for row in rows]
                        total_w=sum(cols); total_h=sum(row_heights)
                        if not cols or total_w<=0 or total_h<=0:
                            continue
                        y_cursor=fy
                        for r_index,row in enumerate(rows):
                            rh=row_heights[r_index] if r_index < len(row_heights) else 0
                            x_cursor=fx
                            grid_index=0
                            cells=[node for node in row if node.tag.endswith('}tc')]
                            for cell_index,cell in enumerate(cells):
                                grid_span=max(1,int(cell.attrib.get('gridSpan','1') or '1'))
                                row_span=max(1,int(cell.attrib.get('rowSpan','1') or '1'))
                                h_merge=str(cell.attrib.get('hMerge','0')).lower() in ('1','true')
                                v_merge=str(cell.attrib.get('vMerge','0')).lower() in ('1','true')
                                span_cols=cols[grid_index:grid_index+grid_span]
                                cw=sum(span_cols)
                                span_rows=row_heights[r_index:r_index+row_span]
                                ch=sum(span_rows)
                                chunks=[]
                                for text_node in cell.iter():
                                    if text_node.tag.endswith('}t') and text_node.text is not None:
                                        chunks.append(str(text_node.text))
                                    elif text_node.tag.endswith('}br'):
                                        chunks.append('\n')
                                text=''.join(chunks)
                                if text and not h_merge and not v_merge and cw>0 and ch>0:
                                    font_sizes=[]
                                    for node in cell.iter():
                                        if node.tag.endswith('}rPr') or node.tag.endswith('}defRPr') or node.tag.endswith('}endParaRPr'):
                                            raw_size=node.attrib.get('sz')
                                            if raw_size is not None:
                                                try:
                                                    font_sizes.append(int(raw_size))
                                                except ValueError:
                                                    pass
                                    fill_rgb=''
                                    solid_fill=next((node for node in cell.iter()
                                                     if node.tag.endswith('}solidFill')),None)
                                    if solid_fill is not None:
                                        rgb=next((node for node in solid_fill.iter()
                                                  if node.tag.endswith('}srgbClr')),None)
                                        if rgb is not None:
                                            fill_rgb=str(rgb.attrib.get('val','')).upper()
                                    shapes.append({
                                        'id': -(frame_id*1000000 + r_index*1000 + grid_index + 1),
                                        'name': f'{frame_name}#r{r_index}c{grid_index}',
                                        'text': text, 'paragraphs':[text],
                                        'geometry': {'x':x_cursor,'y':y_cursor,'w':cw,'h':ch},
                                        'kind':'table-cell','frame_id':frame_id,
                                        'row':r_index,'col':grid_index,
                                        'grid_span':grid_span,'row_span':row_span,
                                        'font_sizes':font_sizes,'fill_rgb':fill_rgb})
                                x_cursor += cw
                                grid_index += grid_span
                            y_cursor += rh
                    key = str(int(number))
                    run_result[key] = parts
                    shape_result[key] = shapes
                    text_result[key] = _semantic_slide_text(shapes)
        except Exception:
            return {}, {}, {}, {}
        return text_result, run_result, shape_result, metadata

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
    deck_text, deck_runs, deck_shapes, deck_file = deck_slide_content(after)
    result = {'window': after, 'target': target, 'controls': controls,
              'focused_control': focused_control, 'deck_slide_text': deck_text,
              'deck_slide_runs': deck_runs, 'deck_slide_shapes': deck_shapes,
              'deck_file': deck_file,
              'hit_owner_id': owner_id,
              'hit_owner_pid': owner_pid, 'screen': [0, 0, image.width, image.height],
              'stable': before == after, 'captured_monotonic_ns': time.monotonic_ns(),
              'screenshot_base64': base64.b64encode(output.getvalue()).decode('ascii')}
    connection.close()
    return result


print(json.dumps(capture(POINT), sort_keys=True))