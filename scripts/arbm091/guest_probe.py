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
import posixpath
import zlib
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


_TEXT_BOX_TEMPLATE_SIZE=(90,28)
_TEXT_BOX_TEMPLATE_SHA256='2cf145b871cf828e198a0ce312a515e07cb2c3e829a09d6a1cb86fb54d1694bb'
_TEXT_BOX_TEMPLATE_ZLIB_B64=(
    'eNrtkt9PglAYhv9yqK3xQyOGF7VM11oX1rp0VhdNbMYompaUabk5PTTLCDJCvnPbOaOzYVdyW7w37Pv28O7bAxhn+Tu54jmS1b5N'
    'n4pT0AEsVf9ZYhwWOT53NMEYOrtyuRW9x4C7RLOPRqWDMQpsuY/Qc2Qp04/NC7akzbWXUaUYgCWc9RpiE2IAlrp6vl8loJ336BCU'
    'jo2tGVvS5jrgzrrnaQ3AcKm4DEjRTG8mb/RE6RYnm09cVDmcDwREpkmuy4AUzUTtyg3GM031F5qpcDO6E97I5CktBqS2AWZBNWDR'
    'xtdDvjsQxvHNDEjd7Gpta2P6y3O4rfuaTjybisuAlJ6d8LQUfO5Uo0Rz7dVpSk9wLdYfz0UDGJDOM7dmk0+E7+Vh0jMv7vWB/s9S'
    'uR0hBmTJkiXL/803Fuswng=='
)

_RADIO_GLYPH_SIZE=(17,17)
_RADIO_UNSELECTED_SHA256='ad803aa2f498c706060a52c7457cc195f685b0f44a331215d2f663cfacefef66'
_RADIO_UNSELECTED_ZLIB_B64=('eNqNjzEOgCAMRe9/FE1EQUz0AB0x0RtgbNwpCatVQRgc7PCStr/9bQi/whld1cNMKbcdIBGC3J98EzY2BN76zr5S5ZkG8jJYGBpzAUdGRYVdw6jLgmAM5cjEmMulK4Nktu0v27C/h7VHnFSAziHoI0n9MjZiWv3n5yc5kwpW')
_RADIO_SELECTED_SHA256='18b7a3b2e19a532e404e1febd36931e8c6e3a165136625e865559627ed1e3cb9'
_RADIO_SELECTED_ZLIB_B64=('eNqNj8EOgjAMhp9oCaiPK0TR+BZL5sgSOE/NApwhhWtJr3YUOHnwP+3/urZ/if4SBqe1C7j53npABG9B/GD6tWDG5b9l395vDZMydgVP9DgqdSiIPFNyQN1JsdJAUDHQSFe1KCc0Ai4CMgHcEtLokxdBvQ4tmCQ5D223tZ/s/Oa1bo5BYA/2nOQxlhLdTftxTWVM3c0/L/8C8w3vUQ==')

_TEXT_OPTIONS_TEMPLATE_SIZE=(150,28)
_TEXT_OPTIONS_TEMPLATE_SHA256='f5b37d1bddcc0222c75aa3ff6e1a7737b5ee84cdaa2b93966354a0e50acf7ff6'
_TEXT_OPTIONS_TEMPLATE_ZLIB_B64=(
    'eNr7/n0UjIJRMApGwSgYBaNgqIJnOMHgdO6oq0ZdNeqqUVeNuoowWBPrVX/2G/Gu2h0WCgTRF4+GA6m8O4Wbvn3bk98DEgvNfAWU'
    '/3asNa3l8NfvD5NDowoXv5wGlVnQ+eX7x01VmROuff/+MHXdt+8fSvZ+/3q4Mn3CVWyWG3pEmYS/IN5Vr+/cqJty+877o2kX7ty5'
    '/2V33tPXZduf3jmfvunOvS9AR+1OWntuQ/L2bw8z9t87Xz/5EVQG6KrPM3P3np2TegXo4PQHYFedSt99YcXEj1hssbzy/cFtkmLw'
    'c8cioPeOZoFC5vv7+qVbq999//4i+xhY8mXBpm/fv+3IffEw8+L3b9tK30JkvgFddTn58vfvX6Z0f36YWTv9C9BV31ZXf8BhBwAy'
    'K4+L'
)


def _exact_gray_matches(haystack,haystack_size,needle,needle_size,region):
    hw,hh=(int(v) for v in haystack_size)
    nw,nh=(int(v) for v in needle_size)
    if hw<=0 or hh<=0 or nw<=0 or nh<=0:
        raise ValueError('TASK091_VISUAL_TEMPLATE_DIMENSIONS_INVALID')
    if len(haystack)!=hw*hh or len(needle)!=nw*nh:
        raise ValueError('TASK091_VISUAL_TEMPLATE_BYTES_INVALID')
    x,y,w,h=(int(v) for v in region)
    left=max(0,x); top=max(0,y)
    right=min(hw,x+w); bottom=min(hh,y+h)
    if right-left<nw or bottom-top<nh:
        return []
    first=needle[:nw]
    matches=[]
    for yy in range(top,bottom-nh+1):
        row=haystack[yy*hw+left:yy*hw+right]
        offset=0
        while True:
            found=row.find(first,offset)
            if found<0:
                break
            xx=left+found
            if all(haystack[(yy+dy)*hw+xx:(yy+dy)*hw+xx+nw]
                   == needle[dy*nw:(dy+1)*nw] for dy in range(1,nh)):
                matches.append([xx,yy,nw,nh])
            offset=found+1
    return matches


def _task091_autofit_radio_controls(gray_bytes,screen_size,active_rect,owner_resolver,application):
    sw,sh=(int(v) for v in screen_size)
    uw,uh=_RADIO_GLYPH_SIZE
    unselected=zlib.decompress(base64.b64decode(_RADIO_UNSELECTED_ZLIB_B64))
    selected=zlib.decompress(base64.b64decode(_RADIO_SELECTED_ZLIB_B64))
    if (hashlib.sha256(unselected).hexdigest()!=_RADIO_UNSELECTED_SHA256 or
        hashlib.sha256(selected).hexdigest()!=_RADIO_SELECTED_SHA256):
        raise RuntimeError('TASK091_AUTOFIT_RADIO_SIGNATURE_CORRUPT')
    ax,ay,aw,ah=(int(v) for v in active_rect)
    region=[ax+int(aw*0.76), ay+int(ah*0.54), int(aw*0.22), int(ah*0.24)]
    rows=[]
    for is_selected,needle in ((False,unselected),(True,selected)):
        for x,y,w,h in _exact_gray_matches(gray_bytes,(sw,sh),needle,(uw,uh),region):
            rows.append({'bbox':[x,y,w,h],'selected':is_selected})
    rows=sorted(rows,key=lambda row:(row['bbox'][1],row['bbox'][0]))
    if not rows:
        return []
    if len(rows)!=3:
        raise RuntimeError('TASK091_AUTOFIT_RADIO_GROUP_AMBIGUOUS')
    xs=[row['bbox'][0] for row in rows]
    ys=[row['bbox'][1] for row in rows]
    if max(xs)-min(xs)>2 or not all(24<=ys[i+1]-ys[i]<=36 for i in range(2)):
        raise RuntimeError('TASK091_AUTOFIT_RADIO_GROUP_GEOMETRY_INVALID')
    if sum(1 for row in rows if row['selected'])!=1:
        raise RuntimeError('TASK091_AUTOFIT_RADIO_SELECTION_AMBIGUOUS')
    labels=('Do not Autofit','Shrink text on overflow','Resize shape to fit text')
    result=[]
    owner_key=None
    for label,row in zip(labels,rows):
        x,y,w,h=row['bbox']; cx=x+w//2; cy=y+h//2
        owner_id,owner_pid=owner_resolver((cx,cy))
        if int(owner_id or 0)<=0 or int(owner_pid or 0)<=0:
            raise RuntimeError('TASK091_AUTOFIT_RADIO_OWNER_UNPROVEN')
        current_owner=(int(owner_id),int(owner_pid))
        if owner_key is None:
            owner_key=current_owner
        elif current_owner!=owner_key:
            raise RuntimeError('TASK091_AUTOFIT_RADIO_OWNER_DRIFT')
        result.append({
            'label':label,'role':'visual-radio','pid':int(owner_pid),
            'application':str(application or ''),'bbox':[x,y,w,h],
            'showing':True,'enabled':True,'focused':False,'depth':4096,
            'selected':bool(row['selected']),'owner_id':int(owner_id),
            'structural_family':'wps-autofit-radio-group-v1',
            'cx':cx,'cy':cy,
        })
    return result


def _task091_panel_disclosure_visual_control(gray_bytes,screen_size,active_rect,owner_resolver,application):
    sw,sh=(int(v) for v in screen_size)
    if len(gray_bytes)!=sw*sh:
        raise ValueError('TASK091_PANEL_VISUAL_BYTES_INVALID')
    ax,ay,aw,ah=(int(v) for v in active_rect)
    rx=max(0,ax+int(aw*0.70)); ry=max(0,ay+int(ah*0.22))
    rr=min(sw,ax+aw); rb=min(sh,ay+int(ah*0.92))
    dark=set()
    for y in range(ry,rb):
        base=y*sw
        for x in range(rx,rr):
            if gray_bytes[base+x] < 100:
                dark.add((x,y))
    candidates=[]
    while dark:
        seed=dark.pop(); stack=[seed]; points=[seed]
        while stack:
            x,y=stack.pop()
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    if dx==0 and dy==0:
                        continue
                    q=(x+dx,y+dy)
                    if q in dark:
                        dark.remove(q); stack.append(q); points.append(q)
        xs=[p[0] for p in points]; ys=[p[1] for p in points]
        x=min(xs); y=min(ys); w=max(xs)-x+1; h=max(ys)-y+1
        if not (4<=w<=8 and 8<=h<=14 and 18<=len(points)<=55):
            continue
        rows=[]; valid=True
        for yy in range(y,y+h):
            row=sorted(px for px,py in points if py==yy)
            if not row:
                continue
            if row[-1]-row[0]+1!=len(row):
                valid=False; break
            rows.append(len(row))
        if not valid or len(rows)<8:
            continue
        peak=max(rows); peak_at=rows.index(peak)
        if peak<4 or peak_at<2 or peak_at>len(rows)-3 or rows[0]>2 or rows[-1]>2:
            continue
        if any(rows[i+1]<rows[i] or rows[i+1]-rows[i]>1 for i in range(peak_at)):
            continue
        if any(rows[i+1]>rows[i] or rows[i]-rows[i+1]>1 for i in range(peak_at,len(rows)-1)):
            continue
        candidates.append([x,y,w,h])
    if not candidates:
        return None
    if len(candidates)!=1:
        raise RuntimeError('TASK091_PANEL_DISCLOSURE_AMBIGUOUS')
    rect=candidates[0]
    x,y,w,h=rect; cx=x+w//2; cy=y+h//2
    owner_id,owner_pid=owner_resolver((cx,cy))
    if int(owner_id or 0)<=0 or int(owner_pid or 0)<=0:
        raise RuntimeError('TASK091_PANEL_DISCLOSURE_OWNER_UNPROVEN')
    crop=bytearray()
    for yy in range(y,y+h):
        crop.extend(gray_bytes[yy*sw+x:yy*sw+x+w])
    return {
        'label':'PANEL DISCLOSURE','role':'visual-disclosure','pid':int(owner_pid),
        'application':str(application or ''),'bbox':rect,'showing':True,'enabled':True,
        'focused':False,'depth':4096,
        'visual_signature_sha256':hashlib.sha256(bytes(crop)).hexdigest(),
        'structural_family':'wps-panel-disclosure-v1',
        'owner_id':int(owner_id),'cx':cx,'cy':cy,
    }


def _task091_text_box_visual_control(gray_bytes,screen_size,active_rect,owner_resolver,application):
    template=zlib.decompress(base64.b64decode(_TEXT_BOX_TEMPLATE_ZLIB_B64))
    if hashlib.sha256(template).hexdigest()!=_TEXT_BOX_TEMPLATE_SHA256:
        raise RuntimeError('TASK091_VISUAL_SIGNATURE_CORRUPT:TEXT_BOX')
    matches=_exact_gray_matches(
        gray_bytes,screen_size,template,_TEXT_BOX_TEMPLATE_SIZE,active_rect)
    if not matches:
        return None
    if len(matches)!=1:
        raise RuntimeError('TASK091_VISUAL_CONTROL_AMBIGUOUS:TEXT_BOX')
    rect=matches[0]
    x,y,w,h=rect
    cx=x+w//2; cy=y+h//2
    owner_id,owner_pid=owner_resolver((cx,cy))
    if int(owner_id or 0)<=0 or int(owner_pid or 0)<=0:
        raise RuntimeError('TASK091_VISUAL_CONTROL_OWNER_UNPROVEN:TEXT_BOX')
    return {
        'label':'Text Box','role':'visual-tab','pid':int(owner_pid),
        'application':str(application or ''),'bbox':rect,'showing':True,'enabled':True,
        'focused':False,'depth':4096,'visual_signature_sha256':_TEXT_BOX_TEMPLATE_SHA256,
        'owner_id':int(owner_id),'cx':cx,'cy':cy,
    }


def _task091_text_options_visual_control(gray_bytes,screen_size,active_rect,owner_resolver,application):
    template=zlib.decompress(base64.b64decode(_TEXT_OPTIONS_TEMPLATE_ZLIB_B64))
    if hashlib.sha256(template).hexdigest()!=_TEXT_OPTIONS_TEMPLATE_SHA256:
        raise RuntimeError('TASK091_VISUAL_SIGNATURE_CORRUPT')
    matches=_exact_gray_matches(
        gray_bytes,screen_size,template,_TEXT_OPTIONS_TEMPLATE_SIZE,active_rect)
    if not matches:
        return None
    if len(matches)!=1:
        raise RuntimeError('TASK091_VISUAL_CONTROL_AMBIGUOUS:TEXT_OPTIONS')
    rect=matches[0]
    x,y,w,h=rect
    cx=x+w//2; cy=y+h//2
    owner_id,owner_pid=owner_resolver((cx,cy))
    if int(owner_id or 0)<=0 or int(owner_pid or 0)<=0:
        raise RuntimeError('TASK091_VISUAL_CONTROL_OWNER_UNPROVEN:TEXT_OPTIONS')
    return {
        'label':'TEXT OPTIONS','role':'visual-tab','pid':int(owner_pid),
        'application':str(application or ''),'bbox':rect,'showing':True,'enabled':True,
        'focused':False,'depth':4096,'visual_signature_sha256':_TEXT_OPTIONS_TEMPLATE_SHA256,
        'owner_id':int(owner_id),'cx':cx,'cy':cy,
    }


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

    def hit_owner(candidate=None):
        candidate = point if candidate is None else candidate
        if candidate is None:
            return 0, 0
        current = root
        chain = []
        for _ in range(32):
            child_hit = None
            for child in reversed(current.query_tree().children[-256:]):
                try:
                    if child.get_attributes().map_state == X.IsViewable and contains(box(child), candidate):
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
            return {}, {}, {}, {}, {}, {}
        text_result = {}
        run_result = {}
        shape_result = {}
        chart_result = {}
        relationship_result = {}
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
                        # Keep non-text shapes too: fills/geometry are semantic
                        # task state (for example the Slide 9 roadmap time-span block).
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
                        body_pr=next((node for node in shape.iter()
                                      if node.tag.endswith('}bodyPr')),None)
                        autofit_mode=''
                        if body_pr is not None:
                            if any(node.tag.endswith('}noAutofit') for node in body_pr):
                                autofit_mode='DO_NOT_AUTOFIT'
                            elif any(node.tag.endswith('}normAutofit') for node in body_pr):
                                autofit_mode='SHRINK_TEXT_ON_OVERFLOW'
                            elif any(node.tag.endswith('}spAutoFit') for node in body_pr):
                                autofit_mode='RESIZE_SHAPE_TO_FIT_TEXT'
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
                                       'font_sizes':font_sizes,'fill_rgb':fill_rgb,
                                       'autofit_mode':autofit_mode})
                    rel_targets={}
                    rel_rows=[]
                    rel_name='ppt/slides/_rels/'+base+'.rels'
                    if rel_name in archive.namelist():
                        try:
                            rel_root=ET.fromstring(archive.read(rel_name))
                            for rel in rel_root:
                                rid=next((v for k,v in rel.attrib.items() if k.endswith('}id') or k=='Id'),'')
                                target=str(rel.attrib.get('Target',''))
                                rel_type=str(rel.attrib.get('Type',''))
                                target_mode=str(rel.attrib.get('TargetMode',''))
                                normalized_target=(posixpath.normpath(posixpath.join('ppt/slides',target))
                                                   if target and target_mode.casefold()!='external'
                                                   else target)
                                if rid and target:
                                    rel_targets[rid]=normalized_target
                                if target:
                                    rel_rows.append({
                                        'type':rel_type,
                                        'target':normalized_target,
                                        'target_mode':target_mode,
                                    })
                            rel_rows=sorted(rel_rows,key=lambda row:(
                                row['type'],row['target_mode'],row['target']))
                        except Exception:
                            rel_targets={}
                            rel_rows=[]
                    charts=[]
                    for frame in root_xml.iter():
                        if not frame.tag.endswith('}graphicFrame'):
                            continue
                        c_nv_pr = next((node for node in frame.iter()
                                      if node.tag.endswith('}cNvPr')), None)
                        frame_id = int(c_nv_pr.attrib.get('id', '0')) if c_nv_pr is not None else 0
                        frame_name = str(c_nv_pr.attrib.get('name', '')) if c_nv_pr is not None else ''
                        chart_ref=next((node for node in frame.iter()
                                       if node.tag.endswith('}chart')),None)
                        if chart_ref is None:
                            continue
                        rid=next((v for k,v in chart_ref.attrib.items() if k.endswith('}id')),'')
                        chart_name=rel_targets.get(rid,'')
                        if not chart_name or chart_name not in archive.namelist():
                            continue
                        try:
                            chart_xml=ET.fromstring(archive.read(chart_name))
                        except Exception:
                            continue
                        series=[]
                        categories=[]
                        for ser in [node for node in chart_xml.iter() if node.tag.endswith('}ser')]:
                            tx=next((node for node in ser if node.tag.endswith('}tx')),None)
                            series_name=''
                            if tx is not None:
                                vals=[str(node.text or '') for node in tx.iter()
                                      if node.tag.endswith('}v') and node.text is not None]
                                if vals:
                                    series_name=vals[0]
                            cat=next((node for node in ser if node.tag.endswith('}cat')),None)
                            if cat is not None and not categories:
                                categories=[str(node.text or '') for node in cat.iter()
                                            if node.tag.endswith('}v') and node.text is not None]
                            val=next((node for node in ser if node.tag.endswith('}val')),None)
                            values=[]
                            if val is not None:
                                for node in val.iter():
                                    if not node.tag.endswith('}v') or node.text is None:
                                        continue
                                    try:
                                        values.append(float(node.text))
                                    except ValueError:
                                        pass
                            series.append({'name':series_name,'values':values})
                        charts.append({'id':frame_id,'name':frame_name,
                                       'chart_part':chart_name,
                                       'categories':categories,'series':series})

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
                    chart_result[key] = charts
                    relationship_result[key] = rel_rows
                    text_result[key] = _semantic_slide_text(shapes)
        except Exception:
            return {}, {}, {}, {}, {}, {}
        return text_result, run_result, shape_result, chart_result, relationship_result, metadata

    before = window_info()
    owner_before_id, owner_before_pid = hit_owner()
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
                app_low=str(application or '').casefold()
                wps_control=(pid == before['pid'] or
                             any(token in app_low for token in ('wps','wpp','kingsoft')))
                if wps_control and in_active_window(rect):
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
        low = name.casefold()
        wps_family = any(token in low for token in ('wps', 'wpp', 'kingsoft'))
        allowed = (pid == before['pid'] or
                   (owner_before_pid and pid == owner_before_pid) or
                   wps_family or
                   low in ('gnome-shell', 'gnome shell', 'unity', 'ubuntu dock'))
        if not allowed:
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
    gray=image.convert('L').tobytes()
    visual_specs=(
        ('TEXT OPTIONS',_task091_text_options_visual_control),
        ('Text Box',_task091_text_box_visual_control),
    )
    for visual_label,resolver in visual_specs:
        if any(str(row.get('label') or '').strip().casefold()==visual_label.casefold()
               for row in controls if isinstance(row,dict)):
            continue
        visual_control=resolver(
            gray, image.size, active_rect, hit_owner,
            before.get('wm_class') or before.get('title') or '')
        if visual_control is None:
            continue
        controls.append(visual_control)
        controls=sorted(controls,key=lambda value:(
            not value.get('focused',False),-int(value.get('depth') or 0),
            value['bbox'][1],value['bbox'][0],value['bbox'][2]*value['bbox'][3]))[:128]
        if point is not None and contains(visual_control['bbox']):
            if target is not None and target != visual_control:
                raise RuntimeError('TASK091_VISUAL_CONTROL_TARGET_AMBIGUOUS:'+visual_label.upper().replace(' ','_'))
            target=visual_control
    if not any(str(row.get('label') or '').strip().casefold() in ('text options','text box')
               for row in controls if isinstance(row,dict)):
        disclosure=_task091_panel_disclosure_visual_control(
            gray,image.size,active_rect,hit_owner,
            before.get('wm_class') or before.get('title') or '')
        if disclosure is not None:
            controls.append(disclosure)
            controls=sorted(controls,key=lambda value:(
                not value.get('focused',False),-int(value.get('depth') or 0),
                value['bbox'][1],value['bbox'][0],value['bbox'][2]*value['bbox'][3]))[:128]
            if point is not None and contains(disclosure['bbox']):
                if target is not None and target != disclosure:
                    raise RuntimeError('TASK091_VISUAL_CONTROL_TARGET_AMBIGUOUS:PANEL_DISCLOSURE')
                target=disclosure
    if any(str(row.get('label') or '').strip().casefold()=='panel disclosure'
           for row in controls if isinstance(row,dict)):
        radios=_task091_autofit_radio_controls(
            gray,image.size,active_rect,hit_owner,
            before.get('wm_class') or before.get('title') or '')
        for radio in radios:
            controls.append(radio)
            if point is not None and contains(radio['bbox']):
                if target is not None and target != radio:
                    raise RuntimeError('TASK091_VISUAL_CONTROL_TARGET_AMBIGUOUS:AUTOFIT_RADIO')
                target=radio
        if radios:
            controls=sorted(controls,key=lambda value:(
                not value.get('focused',False),-int(value.get('depth') or 0),
                value['bbox'][1],value['bbox'][0],value['bbox'][2]*value['bbox'][3]))[:128]
    output = io.BytesIO()
    image.save(output, format='PNG')
    owner_id, owner_pid = hit_owner()
    after = window_info()
    deck_text, deck_runs, deck_shapes, deck_charts, deck_relationships, deck_file = deck_slide_content(after)
    result = {'window': after, 'target': target, 'controls': controls,
              'focused_control': focused_control, 'deck_slide_text': deck_text,
              'deck_slide_runs': deck_runs, 'deck_slide_shapes': deck_shapes,
              'deck_slide_charts': deck_charts, 'deck_slide_relationships': deck_relationships,
              'deck_file': deck_file,
              'hit_owner_id': owner_id,
              'hit_owner_pid': owner_pid, 'screen': [0, 0, image.width, image.height],
              'stable': before == after and
                        (point is None or
                         (owner_before_id, owner_before_pid) == (owner_id, owner_pid)),
              'captured_monotonic_ns': time.monotonic_ns(),
              'screenshot_base64': base64.b64encode(output.getvalue()).decode('ascii')}
    connection.close()
    return result


print(json.dumps(capture(POINT), sort_keys=True))