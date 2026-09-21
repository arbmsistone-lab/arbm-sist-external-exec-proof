"""OpenAI-compatible OSWorld bridge. All guest execution stays in official OSWorld."""
import argparse, json, os, re, time, hashlib, threading
from pathlib import Path
from PIL import Image
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from osworld_ingress import project_messages
from osworld_milestones import Milestones, verified_facts
from osworld_control import canonical_action, ground_action, Verifier, pack_payload, validate_response, visual_reference_recovery, foreground_context, allow_bounded_wps_escape_repeat, allow_bounded_wps_modal_close_repeat, task091_spatial_target_proof
from arbm091.trace_gate import classify as classify_wps_window
from osworld_v32_policy import DecisionKind, apply_live_policy
from osworld_openrouter_free import FREE_ROUTE, prompt as openrouter_prompt
from osworld_groq_free import GROQ_FREE_ROUTE
from osworld_local_vlm import LOCAL_VLM_ROUTE, warm_runtime
from osworld_recovery import recovery_policy, rejects_visual_navigation_loop, semantic_terminal
from osworld_elite_controller import EliteController
from arbm_senior_elite_board import require_unanimous as require_senior_elite
from arbm_safe_http import SafeHttpError, request_json
from osworld_gimp_style_transfer import next_recovery_action
from osworld_061_calibrated_grade import next_calibrated_action, DONE as CAL_DONE

TASK091_REPLACEMENTS = (
    ('Growth Plan Draft','Stabilize-and-Recover Rebaseline'),
    ('Planning posture: accelerate growth through H2 scale-up','Planning posture: stabilize and recover with disciplined sequencing'),
    ('$42.8M','$40.9M'), ('42.8','40.9'),
    ('$2.6M','$2.8M'), ('2.6','2.8'),
    ('112%','104%'), ('112','104'),
    ('74%','71%'), ('74','71'),
    ('19 mo','17 mo'), ('214','206'),
    ('18 open roles remain','8 open roles remain'),
    ('Driven by expansion sprint','Retention recovery remains the focus'),
    ('+0.4','-0.5'), ('+1.2','+0.7'), ('+0.8','-0.6'), ('+0.6','+0.4'), ('+0.5','+1.6'),
    ('New logo mix','Renewal saves'), ('Price uplift','Pricing discipline'),
    ('Usage expansion','Migration delay'), ('Hiring drag','Support credits'),
    ('Partner channel','Partner stabilization'),
    ('International pilot','International Pilot stop'),
    ('Expansion Sprint','Customer Retention Plays'),
    ('International Pilot','Data Migration'),
    ('Data Migration stop','International Pilot stop'),
    ('Platform uplift','Reliability Hardening'),
    ('Regional launch readiness','Vendor SLA breach'),
    ('Data privacy review','Data migration cutover failure'),
    ('Platform & Reliability','Platform / Reliability'),
    ('growth-focused','recovery-focused'), ('accelerating','stabilizing'),
    ('ahead of plan','rebaseline underway'), ('scale-up mode','disciplined sequencing'),
    ('commercial scale-up','recovery plan'),
    ('H2 Growth Roadmap','H2 Stabilize-and-Recover Roadmap'),
    ('Customer Retention Plays launch','Incident runbook rollout'),
    ('Data Migration kickoff','Cutover rehearsal complete'),
    ('Self-serve pricing release','Renewal intervention playbook'),
    ('Regional playbook rollout','Wave 1 migration complete'),
    ('Global launch readiness review','Recovery review with OpCom'),
    ('Sep 01','Aug 22'), ('Sep 15','Sep 19'), ('Oct 03','Oct 10'),
    ('Oct 21','Oct 24'), ('Nov 11','Nov 14'), ('Dec 04','Dec 05'),
    ('Confirm Customer Retention Plays funding','Protect Reliability Hardening capacity'),
    ('Approve Data Migration launch window','Sequence Data Migration cutover'),
    ('Maintain current GTM hiring mix','Freeze non-critical hiring'),
    ('Needed to preserve Q4 upsell upside and Growth Ops hiring plan.','Protect service stability and incident recovery capacity.'),
    ('Maintains current September sequencing and partner onboarding path.','Stage migration cutover against reliability readiness.'),
    ('Supports disciplined sequencing assumptions used in the burn plan.','Keep hiring within the rebased cash envelope.'),
    ('Platform budget still includes reliability capacity as part of one shared pool.','Platform $6.2M and Reliability $3.9M are separate protected pools.'),
    ('No standalone Reliability function appears in the draft.','Reliability is a standalone function at $3.9M.'),
    ('Growth Ops remains funded for customer retention plays execution.','Growth Ops is frozen at $2.0M for H2.'),
    ('Reliability is not split out separately from Platform in either chart or table.','Reliability is standalone with 18 HC and 3 open roles.'),
)

def _task091_match(instruction):
    text=str(instruction or '').casefold()
    return (os.environ.get('TASK_ID')=='091'
            and 'operating committee' in text and 'rebaseline' in text
            and 'reforecast_model_h2.xlsx' in text)

TASK091_SPATIAL_TEXT_EDITS = (
    # slide, x, y, visible draft text, final text
    (1, 745, 335, 'Growth Plan Draft', 'H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'),
    (1, 738, 503, 'Planning posture: accelerate growth through H2 scale-up',
                    'Northstar Cloud\nPrepared for July Operating Committee review\nPlanning posture: stabilize and recover with disciplined sequencing'),
    (1, 1338, 393, '$42.8M', '$40.9M'),
    (1, 1338, 511, '$2.6M', '$2.8M'),
    (1, 1338, 630, '214', '206'),
    (2, 558, 364, '$42.8M', '$40.9M'),
    (2, 792, 364, '112%', '104%'),
    (2, 1026, 364, '$2.6M', '$2.8M'),
    (2, 1245, 364, '19 mo', '17 mo'),
    (2, 1439, 364, '214', '206'),
    # KPI scorecard structured H2 column.
    (3, 843, 404, '$42.8M', '$40.9M'),
    (3, 843, 465, '112%', '104%'),
    (3, 843, 525, '74%', '71%'),
    (3, 843, 586, '$2.6M', '$2.8M'),
    (3, 843, 646, '2', '3'),
    (3, 843, 707, '214', '206'),
    # ARR bridge individual value/label shapes.
    (4, 617, 360, '+1.2', '+0.7'),
    (4, 615, 752, 'New logo mix', 'Renewal saves'),
    (4, 728, 360, '+0.6', '+0.4'),
    (4, 727, 752, 'Price uplift', 'Pricing discipline'),
    (4, 839, 360, '+0.8', '-0.6'),
    (4, 838, 752, 'Usage expansion', 'Migration delay'),
    (4, 950, 360, '+0.4', '-0.5'),
    (4, 949, 752, 'International pilot', 'Support credits'),
    (4, 1062, 360, '-0.3', '-0.3'),
    (4, 1060, 752, 'Hiring drag', 'International Pilot stop'),
    (4, 1173, 360, '+0.5', '+1.6'),
    (4, 1171, 752, 'Partner channel', 'Partner stabilization'),
    (4, 1284, 360, '42.8', '40.9'),
    # Headcount table: expose separate Reliability and Growth Ops freeze rows.
    (6, 1198, 400, 'Platform & Reliability', 'Platform'),
    (6, 1322, 400, 'Scale up', 'Selective backfill'),
    (6, 1447, 400, '8', '2'),
    (6, 1198, 450, 'Growth Ops', 'Reliability'),
    (6, 1322, 450, 'Expand', 'Protected hiring'),
    (6, 1447, 450, '5', '3'),
    (6, 1198, 500, 'GTM', 'Growth Ops'),
    (6, 1322, 500, 'Selective add', 'Freeze'),
    (6, 1447, 500, '6', '0'),
    # Risk titles: remove closed launch risk and introduce two final H2 risks.
    (7, 717, 383, 'Regional launch readiness', 'Vendor SLA breach'),
    (7, 571, 499, 'Data privacy review', 'Data migration cutover failure'),
    # Dependency map final workstreams.
    (8, 576, 408, 'Platform uplift', 'Reliability Hardening'),
    (8, 850, 408, 'Expansion Sprint', 'Customer Retention Plays'),
    (8, 1123, 408, 'International Pilot', 'Data Migration'),
    # Roadmap visible lanes/text.
    (9, 800, 195, 'H2 Growth Roadmap', 'H2 Stabilize-and-Recover Roadmap'),
    (9, 505, 455, 'Expansion Sprint', 'Reliability Hardening'),
    (9, 901, 453, 'Expansion Sprint', 'Reliability Hardening'),
    (9, 505, 535, 'International Pilot', 'Data Migration'),
    (9, 1013, 533, 'International Pilot', 'Data Migration'),
    # Decision requests.
    (11, 234, 391, 'Confirm Expansion Sprint funding', 'Protect Reliability Hardening capacity'),
    (11, 609, 391, 'Approve International Pilot launch window', 'Sequence Data Migration cutover'),
    (11, 984, 391, 'Maintain current GTM hiring mix', 'Freeze non-critical hiring'),
    # Appendix KPI H2 column.
    (12, 1396, 466, '42.8', '40.9'),
    (12, 1396, 526, '112', '104'),
    (12, 1396, 586, '74', '71'),
    (12, 1396, 646, '2.6', '2.8'),
    (12, 1396, 705, '214', '206'),
    (12, 1396, 765, '2', '3'),
    # Appendix milestone tracker.
    (13, 544, 536, 'Expansion Sprint launch', 'Incident runbook rollout'),
    (13, 804, 536, 'Growth Ops', 'Reliability Hardening'),
    (13, 1064, 536, 'Sep 01', 'Aug 22'),
    (13, 1323, 536, 'Green', 'Amber'),
    (13, 544, 581, 'International Pilot kickoff', 'Cutover rehearsal complete'),
    (13, 804, 581, 'GTM', 'Data Migration'),
    (13, 1064, 581, 'Sep 15', 'Sep 19'),
    (13, 1323, 581, 'Green', 'Amber'),
    (13, 544, 627, 'Self-serve pricing release', 'Renewal intervention playbook'),
    (13, 1064, 627, 'Oct 03', 'Oct 10'),
    (13, 544, 672, 'Renewals dashboard v2', 'Renewals dashboard v2'),
    (13, 1064, 672, 'Oct 21', 'Oct 24'),
    (13, 544, 718, 'Regional playbook rollout', 'Wave 1 migration complete'),
    (13, 804, 718, 'Ops', 'Data Migration'),
    (13, 1064, 718, 'Nov 11', 'Nov 14'),
    (13, 544, 763, 'Global launch readiness review', 'Recovery review with OpCom'),
    (13, 1064, 763, 'Dec 04', 'Dec 05'),
    (13, 1323, 763, 'Red', 'Green'),
)
def _task091_norm(value):
    return ' '.join(str(value or '').replace('\u200b','').casefold().split())

def _task091_slide_text(window_state, slide):
    if not isinstance(window_state,dict):
        return ''
    deck=window_state.get('deck_slide_text',{})
    if not isinstance(deck,dict):
        return ''
    return str(deck.get(str(int(slide)),'') or '')

def _task091_text_count(window_state, slide, value):
    wanted=_task091_norm(value)
    haystack=_task091_norm(_task091_slide_text(window_state,slide))
    return haystack.count(wanted) if wanted else 0

def _task091_canvas_ready(observation, window_state=None):
    low=str(observation or '').casefold()
    deck_markers=('operating committee','growth plan draft','northstar cloud','presentation - wps office')
    if any(x in low for x in deck_markers):
        return True
    deck=window_state.get('deck_slide_text',{}) if isinstance(window_state,dict) else {}
    return isinstance(deck,dict) and bool(deck)

TASK091_TYPE_INTERVAL=0.02
TASK091_REPAIR_TYPE_INTERVAL=0.05

def _task091_needs_explicit_text_mode(old, new):
    """Text mode is established only by a signed text-hit doubleClick.

    WPS 2019 does not reliably enter text editing with F2 after selecting a
    shape. The focal artifact proved F2 left the object selected and Ctrl+A
    then selected the whole slide. Destructive text keys are therefore emitted
    only after the prior atomic action double-clicked a signed point inside the
    target shape's text region.
    """
    return False

def _task091_write_command(value, interval=TASK091_TYPE_INTERVAL, ensure_text_mode=False):
    if ensure_text_mode:
        raise ValueError('TASK091_TEXT_MODE_MUST_BE_POINTER_ESTABLISHED')
    lines=str(value).split('\n')
    commands=["pyautogui.hotkey('ctrl', 'a')"]
    for index,line in enumerate(lines):
        if line:
            commands.append(f"pyautogui.write({line!r}, interval={float(interval):g})")
        if index + 1 < len(lines):
            commands.append("pyautogui.hotkey('shift', 'enter')")
    return '\n'.join(commands)

def _task091_table_cell_bounded_write_command(old, new, interval=TASK091_TYPE_INTERVAL):
    """Replace one single-line cell value without any global selection command."""
    old=str(old or '')
    new=str(new or '')
    if not old or '\n' in old or '\n' in new or len(old) > 64 or len(new) > 128:
        raise ValueError('TASK091_TABLE_CELL_BOUNDED_EDIT_INVALID')
    commands=["pyautogui.press('end')",
              f"pyautogui.press('backspace', presses={len(old)}, interval=0.03)"]
    if new:
        commands.append(f"pyautogui.write({new!r}, interval={float(interval):g})")
    return '\n'.join(commands)

def _task091_foreground_sha(window_state):
    window=window_state.get('window',{}) if isinstance(window_state,dict) else {}
    payload=json.dumps(window,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest() if window else ''


def _task091_window_state():
    root=os.environ.get('ARBM_WPS_EVIDENCE_DIR')
    if not root:
        return None
    path=Path(root)/'window-state.json'
    if not path.is_file():
        return None
    try:
        value=json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return None
    if value.get('schema') != 1 or value.get('stable') is not True or not isinstance(value.get('window'),dict):
        return None
    return value

def _task091_screenshot_path(window_state):
    if not isinstance(window_state,dict):
        return None
    root=os.environ.get('ARBM_WPS_EVIDENCE_DIR')
    source=str(window_state.get('source') or '')
    if not root or not re.fullmatch(r'\d{4}-\d{2}-(?:before|after)',source):
        return None
    path=Path(root)/'wps-observations'/(source+'.png')
    return path if path.is_file() else None

def _task091_screenshot_source_path(source):
    root=os.environ.get('ARBM_WPS_EVIDENCE_DIR')
    source=str(source or '')
    if not root or not re.fullmatch(r'\d{4}-\d{2}-(?:before|after)',source):
        return None
    path=Path(root)/'wps-observations'/(source+'.png')
    return path if path.is_file() else None

def _task091_caret_delta_geometry(before_source, after_source, bbox):
    """Prove a text caret from a narrow vertical pixel delta inside one cell."""
    before_path=_task091_screenshot_source_path(before_source)
    after_path=_task091_screenshot_source_path(after_source)
    if before_path is None or after_path is None or not isinstance(bbox,list) or len(bbox)!=4:
        return {'proven':False,'reason':'evidence-missing'}
    if not all(type(v) is int for v in bbox):
        return {'proven':False,'reason':'bbox-invalid'}
    x,y,w,h=bbox
    if w<=0 or h<=0:
        return {'proven':False,'reason':'bbox-empty'}
    try:
        with Image.open(before_path) as a_img, Image.open(after_path) as b_img:
            a=a_img.convert('RGB').crop((x,y,x+w,y+h))
            b=b_img.convert('RGB').crop((x,y,x+w,y+h))
            if a.size != b.size:
                return {'proven':False,'reason':'size-drift'}
            xs=[]; ys=[]; col_counts={}
            for py in range(h):
                for px in range(w):
                    av=a.getpixel((px,py)); bv=b.getpixel((px,py))
                    if max(abs(int(av[i])-int(bv[i])) for i in range(3)) <= 20:
                        continue
                    xs.append(px); ys.append(py); col_counts[px]=col_counts.get(px,0)+1
    except Exception:
        return {'proven':False,'reason':'image-read-failed'}
    count=len(xs)
    if not count:
        return {'proven':False,'reason':'no-local-delta','count':0}
    dw=max(xs)-min(xs)+1; dh=max(ys)-min(ys)+1
    dominant=max(col_counts.values()) if col_counts else 0
    proven=(8 <= count <= 160
            and dw <= 4
            and 8 <= dh <= min(40,h)
            and dh >= max(8,dw*4)
            and dominant >= max(8,int(count*0.65)))
    return {'proven':proven,'reason':'caret-geometry' if proven else 'delta-not-caret',
            'count':count,'width':dw,'height':dh,'dominant_column':dominant,
            'bbox':[min(xs),min(ys),dw,dh]}

def _task091_table_cell_text_ink_point(window_state, bbox, inset=8, threshold=24):
    """Derive a click point from observed text ink inside one proven table cell.

    The PPTX geometry proves which cell is targeted; the current screenshot proves
    where visible glyph ink actually sits inside that cell. Borders are excluded,
    the dominant interior background is estimated by per-channel median, and only
    bounded high-contrast ink is admitted.
    """
    path=_task091_screenshot_path(window_state)
    if path is None or not isinstance(bbox,list) or len(bbox)!=4:
        return None
    if not all(type(v) is int for v in bbox):
        return None
    x,y,w,h=bbox
    if w <= 2*inset+4 or h <= 2*inset+4:
        return None
    try:
        with Image.open(path) as image:
            rgb=image.convert('RGB')
            left=x+inset; top=y+inset; right=x+w-inset; bottom=y+h-inset
            crop=rgb.crop((left,top,right,bottom))
            iw,ih=crop.size
            pixels=list(crop.getdata())
    except Exception:
        return None
    if not pixels:
        return None
    channels=[]
    for channel in range(3):
        values=sorted(int(px[channel]) for px in pixels)
        channels.append(values[len(values)//2])
    background=tuple(channels)
    xs=[]; ys=[]
    for py in range(ih):
        for px in range(iw):
            value=crop.getpixel((px,py))
            if max(abs(int(value[i])-background[i]) for i in range(3)) < int(threshold):
                continue
            xs.append(px); ys.append(py)
    count=len(xs)
    if count < 12 or count > min(2000,max(12,(iw*ih)//2)):
        return None
    ink_w=max(xs)-min(xs)+1; ink_h=max(ys)-min(ys)+1
    if ink_w < 2 or ink_h < 5 or ink_h > min(40,ih) or ink_w > iw-2:
        return None
    cx=left+int(round(sum(xs)/count))
    cy=top+int(round(sum(ys)/count))
    if not (left <= cx < right and top <= cy < bottom):
        return None
    payload={
        'source':str(window_state.get('source') or ''),
        'screenshot_sha256':str(window_state.get('screenshot_sha256') or ''),
        'cell_bbox':[x,y,w,h],
        'background':list(background),
        'threshold':int(threshold),
        'ink_bbox':[left+min(xs),top+min(ys),ink_w,ink_h],
        'ink_pixels':count,
        'point':[cx,cy],
    }
    proof=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {**payload,'cx':cx,'cy':cy,'proof_sha256':proof}

def _task091_region_sha256(window_state, bbox, inset=6):
    path=_task091_screenshot_path(window_state)
    if path is None or not isinstance(bbox,list) or len(bbox)!=4:
        return ''
    if not all(type(v) is int for v in bbox):
        return ''
    x,y,w,h=bbox
    if w <= 2*inset or h <= 2*inset:
        return ''
    try:
        with Image.open(path) as image:
            rgb=image.convert('RGB')
            left=max(0,x+inset); top=max(0,y+inset)
            right=min(rgb.width,x+w-inset); bottom=min(rgb.height,y+h-inset)
            if right <= left or bottom <= top:
                return ''
            payload=rgb.crop((left,top,right,bottom)).tobytes()
    except Exception:
        return ''
    return hashlib.sha256(payload).hexdigest()

def _task091_table_visual_signature(window_state, slide, frame_id, exclude_shape_id=None):
    rows=[]
    for row in _task091_shape_rows(window_state,slide):
        if str(row.get('kind') or '') != 'table-cell':
            continue
        if int(row.get('frame_id') or 0) != int(frame_id or 0):
            continue
        if exclude_shape_id is not None and int(row.get('id') or 0) == int(exclude_shape_id):
            continue
        box=_task091_shape_bbox(window_state,row)
        if box is None:
            return ''
        digest=_task091_region_sha256(
            window_state,[int(box['x']),int(box['y']),int(box['w']),int(box['h'])])
        if len(digest)!=64:
            return ''
        rows.append((int(row.get('id') or 0),str(row.get('name') or ''),digest))
    if not rows:
        return ''
    rows.sort()
    payload=json.dumps(rows,separators=(',',':'),ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()

def _task091_atspi_candidates(observation, label):
    wanted=' '.join(str(label or '').replace('\u200b','').casefold().split())
    hits=[]
    for line in str(observation or '').splitlines():
        cols=line.split('\t')
        if len(cols)<7:
            continue
        role=str(cols[0] or '').strip()
        name=str(cols[1] or cols[2] or '').replace('\u200b','').strip()
        norm=' '.join(name.casefold().split())
        if not norm or not wanted or (norm!=wanted and wanted not in norm):
            continue
        xy=re.findall(r'-?\d+',cols[-2]); wh=re.findall(r'\d+',cols[-1])
        if len(xy)!=2 or len(wh)!=2:
            continue
        x,y=map(int,xy); w,h=map(int,wh)
        if w<=0 or h<=0:
            continue
        hits.append({'role':role,'label':name,'x':x,'y':y,'w':w,'h':h,
                     'cx':x+w//2,'cy':y+h//2})
    return hits

def _task091_target_resolution(observation, label, hint_x, hint_y):
    hits=_task091_atspi_candidates(observation,label)
    if not hits:
        return 'missing',None
    hits.sort(key=lambda row:((row['cx']-int(hint_x))**2+(row['cy']-int(hint_y))**2,
                              row['w']*row['h'],row['role'],row['label']))
    best=hits[0]
    if len(hits)>1:
        first=(best['cx']-int(hint_x))**2+(best['cy']-int(hint_y))**2
        second=(hits[1]['cx']-int(hint_x))**2+(hits[1]['cy']-int(hint_y))**2
        if first==second:
            return 'ambiguous',None
    return 'visible',best

def _task091_dynamic_target(observation, label, hint_x, hint_y):
    status,target=_task091_target_resolution(observation,label,hint_x,hint_y)
    return target if status=='visible' else None

TASK091_CANONICAL_SCREEN=[0,0,1920,1080]
TASK091_CANONICAL_WINDOW=[70,27,1850,1053]
TASK091_CANONICAL_SLIDE_VIEWPORT=[443,194,1413,795]

def _task091_shape_rows(window_state, slide):
    if not isinstance(window_state,dict):
        return []
    table=window_state.get('deck_slide_shapes',{})
    rows=table.get(str(int(slide)),[]) if isinstance(table,dict) else []
    return rows if isinstance(rows,list) else []

def _task091_shape_by_id(window_state, slide, shape_id):
    matches=[row for row in _task091_shape_rows(window_state,slide)
             if int(row.get('id') or 0)==int(shape_id or 0)]
    return matches[0] if len(matches)==1 else None

def _task091_shape_for_old(window_state, slide, old, hint_x=None, hint_y=None):
    wanted=_task091_norm(old)
    matches=[]
    for row in _task091_shape_rows(window_state,slide):
        text=_task091_norm(row.get('text'))
        geometry=row.get('geometry')
        if (wanted and wanted in text and isinstance(geometry,dict)
                and int(geometry.get('w') or 0)>0 and int(geometry.get('h') or 0)>0):
            matches.append(row)
    if not matches:
        return None
    exact=[row for row in matches if _task091_norm(row.get('text'))==wanted]
    pool=exact or matches
    if hint_x is None or hint_y is None:
        return pool[0] if len(pool)==1 else None
    scored=[]
    for row in pool:
        point=_task091_shape_center(window_state,row)
        if point is None:
            continue
        distance=(int(point['cx'])-int(hint_x))**2+(int(point['cy'])-int(hint_y))**2
        scored.append((distance,int(row.get('id') or 0),str(row.get('name') or ''),row))
    if not scored:
        return None
    scored.sort(key=lambda item:(item[0],item[1],item[2]))
    if len(scored)>1 and scored[0][0]==scored[1][0]:
        return None
    return scored[0][3]

def _task091_shape_bbox(window_state, row):
    if not isinstance(window_state,dict) or not isinstance(row,dict):
        return None
    if window_state.get('screen') != TASK091_CANONICAL_SCREEN:
        return None
    if (window_state.get('window') or {}).get('bbox') != TASK091_CANONICAL_WINDOW:
        return None
    deck_file=window_state.get('deck_file') or {}
    slide_size=deck_file.get('slide_size') if isinstance(deck_file,dict) else None
    if not isinstance(slide_size,dict):
        return None
    sw=int(slide_size.get('w') or 0); sh=int(slide_size.get('h') or 0)
    if sw<=0 or sh<=0:
        return None
    geometry=row.get('geometry') or {}
    gx=int(geometry.get('x') or 0); gy=int(geometry.get('y') or 0)
    gw=int(geometry.get('w') or 0); gh=int(geometry.get('h') or 0)
    if gx<0 or gy<0 or gw<=0 or gh<=0:
        return None
    vx,vy,vw,vh=TASK091_CANONICAL_SLIDE_VIEWPORT
    left=round(vx + (gx/sw)*vw)
    top=round(vy + (gy/sh)*vh)
    right=round(vx + ((gx+gw)/sw)*vw)
    bottom=round(vy + ((gy+gh)/sh)*vh)
    left=max(vx,int(left)); top=max(vy,int(top))
    right=min(vx+vw,int(right)); bottom=min(vy+vh,int(bottom))
    if right-left < 2 or bottom-top < 2:
        return None
    return {'shape':row,'x':left,'y':top,'w':right-left,'h':bottom-top,
            'cx':left+(right-left)//2,'cy':top+(bottom-top)//2}

def _task091_shape_center(window_state, row):
    box=_task091_shape_bbox(window_state,row)
    if box is None:
        return None
    return {'shape':row,'cx':int(box['cx']),'cy':int(box['cy']),
            'shape_bbox':[int(box['x']),int(box['y']),int(box['w']),int(box['h'])]}

def _task091_shape_text_point(window_state, row, hint_x, hint_y, tolerance=32):
    box=_task091_shape_bbox(window_state,row)
    if box is None or hint_x is None or hint_y is None:
        return None
    hx=int(hint_x); hy=int(hint_y)
    left=int(box['x']); top=int(box['y'])
    right=left+int(box['w'])-1; bottom=top+int(box['h'])-1
    dx=(left-hx) if hx<left else ((hx-right) if hx>right else 0)
    dy=(top-hy) if hy<top else ((hy-bottom) if hy>bottom else 0)
    if max(dx,dy) > int(tolerance):
        return None
    inset_x=min(4,max(0,(int(box['w'])-1)//4))
    inset_y=min(4,max(0,(int(box['h'])-1)//4))
    lo_x=left+inset_x; hi_x=right-inset_x
    lo_y=top+inset_y; hi_y=bottom-inset_y
    if lo_x>hi_x or lo_y>hi_y:
        return None
    tx=min(max(hx,lo_x),hi_x)
    ty=min(max(hy,lo_y),hi_y)
    return {'shape':row,'cx':int(tx),'cy':int(ty),
            'shape_bbox':[left,top,int(box['w']),int(box['h'])],
            'shape_center_cx':int(box['cx']),'shape_center_cy':int(box['cy']),
            'hint_x':hx,'hint_y':hy}

def _task091_drift_safe_text_point(window_state, row, hint_x, hint_y, recovery_attempt=0):
    """Project a stale historical hint into the interior of the proven text shape.

    A drifted hint must never be clamped to the shape edge: WPS can interpret an
    edge hit as object selection rather than text editing. Keep the hint's
    horizontal side, prefer the vertical text band, and move boundedly inward on
    a retry. This is geometry-only and remains scoped to the exact proven shape.
    """
    box=_task091_shape_bbox(window_state,row)
    if box is None or hint_x is None or hint_y is None:
        return None
    hx=int(hint_x); hy=int(hint_y)
    left=int(box['x']); top=int(box['y'])
    width=int(box['w']); height=int(box['h'])
    right=left+width-1; bottom=top+height-1
    max_inset_x=max(0,(width-1)//3)
    max_inset_y=max(0,(height-1)//3)
    inset_x=min(max_inset_x,max(4,min(32,max(1,width//10))))
    inset_y=min(max_inset_y,max(2,min(10,max(1,height//4))))
    lo_x=left+inset_x; hi_x=right-inset_x
    lo_y=top+inset_y; hi_y=bottom-inset_y
    if lo_x>hi_x or lo_y>hi_y:
        return None
    if hx < left:
        tx=lo_x
    elif hx > right:
        tx=hi_x
    else:
        tx=min(max(hx,lo_x),hi_x)
    if hy < top or hy > bottom:
        ty=top+height//2
    else:
        ty=min(max(hy,lo_y),hi_y)
    retry=max(0,min(2,int(recovery_attempt or 0)))
    if retry:
        step=max(4,min(18,max(1,width//16)))
        center=int(box['cx'])
        if tx <= center:
            tx=min(hi_x,tx+step*retry)
        else:
            tx=max(lo_x,tx-step*retry)
    return {'shape':row,'cx':int(tx),'cy':int(ty),
            'shape_bbox':[left,top,width,height],
            'shape_center_cx':int(box['cx']),'shape_center_cy':int(box['cy']),
            'hint_x':hx,'hint_y':hy,'recovery_attempt':retry}


def _task091_shape_point(window_state, slide, old, hint_x=None, hint_y=None):
    row=_task091_shape_for_old(window_state,slide,old,hint_x,hint_y)
    if row is None:
        return None
    if str(row.get('kind') or '') == 'table-cell':
        box=_task091_shape_bbox(window_state,row)
        if box is None:
            return None
        cx=int(box['cx']); cy=int(box['cy'])
        hx=int(hint_x) if hint_x is not None else cx
        hy=int(hint_y) if hint_y is not None else cy
        return {'shape':row,'cx':cx,'cy':cy,
                'shape_bbox':[int(box['x']),int(box['y']),int(box['w']),int(box['h'])],
                'shape_center_cx':cx,'shape_center_cy':cy,
                'hint_x':hx,'hint_y':hy,
                'selection_basis':'pptx-table-cell-geometry',
                'hint_drift':int(max(abs(cx-hx),abs(cy-hy)))}
    point=_task091_shape_text_point(window_state,row,hint_x,hint_y)
    if point is not None:
        point['selection_basis']='hint-within-tolerance'
        point['hint_drift']=0
        return point

    # A historical screen hint is advisory, never more authoritative than a
    # unique exact-text shape proven in the active target slide of the PPTX.
    # If the hint drifts after WPS/layout changes, keep fail-closed semantics
    # for ambiguity, but derive a safe in-shape point from canonical geometry.
    wanted=_task091_norm(old)
    exact=[]
    for candidate in _task091_shape_rows(window_state,slide):
        geometry=candidate.get('geometry')
        if (_task091_norm(candidate.get('text'))==wanted
                and isinstance(geometry,dict)
                and int(geometry.get('w') or 0)>0 and int(geometry.get('h') or 0)>0):
            exact.append(candidate)
    if len(exact) != 1 or int(exact[0].get('id') or 0) != int(row.get('id') or 0):
        return None
    box=_task091_shape_bbox(window_state,row)
    if box is None or hint_x is None or hint_y is None:
        return None
    hx=int(hint_x); hy=int(hint_y)
    left=int(box['x']); top=int(box['y'])
    right=left+int(box['w'])-1; bottom=top+int(box['h'])-1
    dx=(left-hx) if hx<left else ((hx-right) if hx>right else 0)
    dy=(top-hy) if hy<top else ((hy-bottom) if hy>bottom else 0)
    point=_task091_drift_safe_text_point(window_state,row,hint_x,hint_y)
    if point is None:
        return None
    point['selection_basis']='unique-exact-pptx-geometry'
    point['hint_drift']=int(max(dx,dy))
    return point

def _task091_nav_command(current_slide, target_slide):
    delta=int(target_slide)-int(current_slide)
    if delta == 0:
        return None
    key='pagedown' if delta>0 else 'pageup'
    return "pyautogui.press(%r, presses=%d, interval=0.12)" % (key, abs(delta))

def _task091_terminal(reason,state):
    state['terminal_reason']=str(reason)
    return {'action':'terminal','reason':str(reason),'specialist_phase':'terminal'}

def _task091_system_check_close(window_state):
    controls=window_state.get('controls',[]) if isinstance(window_state,dict) else []
    candidates=[]
    for row in controls:
        if not isinstance(row,dict):
            continue
        if str(row.get('label','')).strip().casefold() != 'close':
            continue
        if str(row.get('role','')).strip().casefold() not in ('push button','push-button','button'):
            continue
        if row.get('enabled') is not True or row.get('showing') is not True:
            continue
        bbox=row.get('bbox')
        if not (isinstance(bbox,list) and len(bbox)==4 and all(type(v) is int for v in bbox)):
            continue
        x,y,w,h=bbox
        if w<=0 or h<=0:
            continue
        candidates.append({**row,'cx':x+w//2,'cy':y+h//2})
    if len(candidates) != 1:
        return None, ('TASK091_TARGET_AMBIGUOUS' if len(candidates)>1 else 'TASK091_TARGET_NOT_VISIBLE')
    return candidates[0], None


def _task091_same_region(hit,bbox):
    if not isinstance(hit,dict) or not isinstance(bbox,list) or len(bbox)!=4:
        return False
    x,y,w,h=bbox
    cx=x+w//2; cy=y+h//2
    tolerance=max(120,int(max(w,h)*1.75))
    return abs(int(hit.get('cx',0))-cx)<=tolerance and abs(int(hit.get('cy',0))-cy)<=tolerance

def _task091_restricted_repair_plan(actual, expected):
    actual=str(actual or '')
    expected=str(expected or '')
    if not actual or not expected or actual == expected:
        return None
    work=list(actual)
    operations=[]
    cursor=0
    wanted=0
    while wanted < len(expected):
        if cursor < len(work) and work[cursor] == expected[wanted]:
            cursor += 1
            wanted += 1
            continue
        if expected[wanted] == '\n':
            work.insert(cursor,'\n')
            operations.append({'op':'linebreak','index':cursor})
            cursor += 1
            wanted += 1
            continue
        if cursor >= len(work):
            return None
        operations.append({'op':'delete','index':cursor,'char':work[cursor]})
        del work[cursor]
    while cursor < len(work):
        operations.append({'op':'delete','index':cursor,'char':work[cursor]})
        del work[cursor]
    if ''.join(work) != expected:
        return None
    if not operations:
        return None
    if any(row.get('op') not in ('delete','linebreak') for row in operations):
        return None
    return operations

def _task091_delete_only_plan(actual, expected):
    plan=_task091_restricted_repair_plan(actual,expected)
    if not plan or any(row.get('op')!='delete' for row in plan):
        return None
    return [int(row['index']) for row in plan]

def _task091_corrupt_shape(window_state, slide, expected):
    if not isinstance(window_state,dict):
        return None,None
    table=window_state.get('deck_slide_shapes',{})
    rows=table.get(str(int(slide)),[]) if isinstance(table,dict) else []
    matches=[]
    for row in rows if isinstance(rows,list) else []:
        text=str(row.get('text') or '')
        plan=_task091_restricted_repair_plan(text,expected)
        if plan:
            matches.append((row,plan))
    if len(matches)!=1:
        return None,None
    return matches[0]

def _task091_apply_repair_operation(text, operation):
    text=str(text or '')
    if not isinstance(operation,dict) or operation.get('op') not in ('delete','linebreak'):
        raise ValueError('TASK091_REPAIR_OPERATION_INVALID')
    index=int(operation.get('index') if operation.get('index') is not None else -1)
    if index < 0 or index > len(text):
        raise ValueError('TASK091_REPAIR_OPERATION_INDEX_INVALID')
    if operation['op']=='delete':
        if index >= len(text):
            raise ValueError('TASK091_REPAIR_DELETE_INDEX_INVALID')
        expected_char=operation.get('char')
        if expected_char is not None and str(expected_char) != text[index]:
            raise ValueError('TASK091_REPAIR_DELETE_CHAR_MISMATCH')
        return text[:index] + text[index+1:]
    return text[:index] + '\n' + text[index:]


def _task091_other_shapes_signature(window_state, slide, target_shape_id):
    rows=[]
    for row in _task091_shape_rows(window_state,slide):
        if int(row.get('id') or 0)==int(target_shape_id or 0):
            continue
        rows.append({'id':int(row.get('id') or 0),
                     'name':str(row.get('name') or ''),
                     'text':str(row.get('text') or ''),
                     'geometry':dict(row.get('geometry') or {})})
    rows.sort(key=lambda row:(row['id'],row['name']))
    payload=json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _task091_restricted_repair_command(plan):
    if not isinstance(plan,list) or len(plan)!=1:
        raise ValueError('TASK091_REPAIR_ATOMIC_OPERATION_REQUIRED')
    row=plan[0]
    if not isinstance(row,dict) or row.get('op') not in ('delete','linebreak'):
        raise ValueError('TASK091_REPAIR_PLAN_INVALID')
    target=int(row.get('index') if row.get('index') is not None else -1)
    if target < 0:
        raise ValueError('TASK091_REPAIR_OPERATION_INDEX_INVALID')
    commands=["pyautogui.hotkey('ctrl', 'a')","pyautogui.press('left')"]
    remaining=target
    while remaining:
        chunk=min(30,remaining)
        commands.append(f"pyautogui.press('right', presses={chunk}, interval=0.02)")
        remaining-=chunk
    if row['op']=='delete':
        commands.append("pyautogui.press('delete')")
    else:
        commands.append("pyautogui.hotkey('shift', 'enter')")
    if len(commands) > 8:
        raise ValueError('TASK091_REPAIR_ACTION_COUNT_UNBOUNDED')
    return '\n'.join(commands)

def _task091_delete_repair_command(delete_indices):
    indices=[int(value) for value in delete_indices]
    if len(indices)!=1:
        raise ValueError('TASK091_REPAIR_ATOMIC_OPERATION_REQUIRED')
    return _task091_restricted_repair_command([{'op':'delete','index':indices[0]}])

def _task091_verify_pending(observation,pending,window_state):
    slide=int(pending.get('slide') or 0)
    before_old=int(pending.get('before_old_count') or 0)
    before_new=int(pending.get('before_new_count') or 0)
    after_old=_task091_text_count(window_state,slide,pending.get('old'))
    after_new=_task091_text_count(window_state,slide,pending.get('new'))
    before_sha=str(pending.get('before_deck_sha256') or '')
    after_file=window_state.get('deck_file',{}) if isinstance(window_state,dict) else {}
    after_sha=str(after_file.get('sha256') or '') if isinstance(after_file,dict) else ''
    repair_before=str(pending.get('repair_before_deck_sha256') or '')
    repair_persisted=(not repair_before or (len(repair_before)==64 and after_sha != repair_before))
    disk_mutated=(len(before_sha)==64 and len(after_sha)==64 and after_sha != before_sha)
    expected_shape_id=int(pending.get('shape_id') or 0)
    expected_shape=_task091_shape_by_id(window_state,slide,expected_shape_id)
    exact_shape_text=(isinstance(expected_shape,dict)
                      and str(expected_shape.get('text') or '')==str(pending.get('new') or ''))
    current_sibling_signature=_task091_other_shapes_signature(window_state,slide,expected_shape_id)
    before_sibling_signature=str(pending.get('before_sibling_signature') or '')
    collateral_mutation=(disk_mutated
                         and isinstance(expected_shape,dict)
                         and str(expected_shape.get('text') or '')==str(pending.get('old') or '')
                         and bool(before_sibling_signature)
                         and current_sibling_signature != before_sibling_signature)
    if collateral_mutation:
        return False,'collateral-mutation',{'source':'target-pptx','slide':slide,
                                           'shape_id':expected_shape_id,
                                           'sha256_before':before_sha,'sha256_after':after_sha,
                                           'actual_shape_text':str(expected_shape.get('text') or ''),
                                           'expected_shape_text':str(pending.get('new') or ''),
                                           'sibling_signature_before':before_sibling_signature,
                                           'sibling_signature_after':current_sibling_signature}
    disk_verified=(disk_mutated and repair_persisted
                   and before_old > 0 and after_old < before_old and after_new > before_new
                   and exact_shape_text)
    if disk_verified:
        return True,'disk-verified',{'source':'target-pptx','slide':slide,
                                    'shape_id':expected_shape_id,
                                    'old_count_before':before_old,'old_count_after':after_old,
                                    'new_count_before':before_new,'new_count_after':after_new,
                                    'sha256_before':before_sha,'sha256_after':after_sha,
                                    'repair_sha256_before':repair_before or None}
    if disk_mutated and before_old > 0 and after_old < before_old:
        # The normalized target can already be present while WPS has persisted
        # a structurally different textbox (for example one extra paragraph
        # break). That is not "unverified": it is a proven, bounded text
        # mismatch and must flow into the existing atomic repair path.
        semantic_target_present=(after_new > before_new)
        if not semantic_target_present or not exact_shape_text:
            return False,'disk-text-mismatch',{'source':'target-pptx','slide':slide,
                                              'shape_id':expected_shape_id,
                                              'old_count_before':before_old,'old_count_after':after_old,
                                              'new_count_before':before_new,'new_count_after':after_new,
                                              'sha256_before':before_sha,'sha256_after':after_sha,
                                              'semantic_target_present':semantic_target_present,
                                              'exact_shape_text':exact_shape_text,
                                              'actual_shape_text':str(expected_shape.get('text') or '') if isinstance(expected_shape,dict) else None,
                                              'expected_shape_text':str(pending.get('new') or '')}
    bbox=pending.get('target',{}).get('bbox')
    old_hits=_task091_atspi_candidates(observation,pending.get('old'))
    status,new_hit=_task091_target_resolution(
        observation,pending.get('new'),
        pending.get('target',{}).get('cx',0),pending.get('target',{}).get('cy',0))
    old_same=any(_task091_same_region(hit,bbox) for hit in old_hits) if bbox else bool(old_hits)
    new_same=(status=='visible' and (not bbox or _task091_same_region(new_hit,bbox)))
    return bool(new_same and not old_same),status,new_hit

def _task091_prepare_atomic_repair(pending, window_state, state):
    current_file=window_state.get('deck_file',{}) if isinstance(window_state,dict) else {}
    current_sha=str(current_file.get('sha256') or '') if isinstance(current_file,dict) else ''
    corrupt_shape,repair_plan=_task091_corrupt_shape(window_state,pending['slide'],pending['new'])
    if len(current_sha)!=64 or corrupt_shape is None or not repair_plan:
        return _task091_terminal('TASK091_EDIT_TEXT_MISMATCH_UNPROVEN',state)
    if int(corrupt_shape.get('id') or 0) != int(pending.get('shape_id') or 0):
        return _task091_terminal('TASK091_RESTRICTED_REPAIR_SHAPE_DRIFT',state)
    delete_count=sum(1 for row in repair_plan if row.get('op')=='delete')
    linebreak_count=sum(1 for row in repair_plan if row.get('op')=='linebreak')
    if len(repair_plan)>8 or delete_count>8 or linebreak_count>2:
        return _task091_terminal('TASK091_EDIT_TEXT_CORRUPTION_EXCESSIVE',state)
    if any(row.get('op') not in ('delete','linebreak') for row in repair_plan):
        return _task091_terminal('TASK091_EDIT_TEXT_MISMATCH_UNPROVEN',state)
    steps=int(pending.get('repair_steps') or 0)
    if steps>=8:
        return _task091_terminal('TASK091_EDIT_TEXT_CORRUPTION_EXCESSIVE',state)
    hint_x=pending.get('text_hit_x',pending.get('target',{}).get('cx'))
    hint_y=pending.get('text_hit_y',pending.get('target',{}).get('cy'))
    repair_point=_task091_shape_text_point(window_state,corrupt_shape,hint_x,hint_y)
    if repair_point is None:
        return _task091_terminal('TASK091_RESTRICTED_REPAIR_GEOMETRY_UNPROVEN',state)
    current_text=str(corrupt_shape.get('text') or '')
    operation=dict(repair_plan[0])
    try:
        expected_after=_task091_apply_repair_operation(current_text,operation)
    except ValueError:
        return _task091_terminal('TASK091_REPAIR_OPERATION_INVALID',state)
    cx=int(repair_point['cx']); cy=int(repair_point['cy'])
    repaired_target={'source':'task091-pptx-canonical','label':current_text,
                     'role':'task091-canonical-point','slide':int(pending['slide']),
                     'x':cx-1,'y':cy-1,'w':2,'h':2,'cx':cx,'cy':cy,
                     'foreground_sha256':_task091_foreground_sha(window_state),
                     'deck_sha256':current_sha}
    repaired_target['proof_sha256']=task091_spatial_target_proof(repaired_target)
    pending['repair_steps']=steps+1
    pending['repair_attempts']=steps+1
    pending['repair_before_deck_sha256']=current_sha
    pending['repair_before_text']=current_text
    pending['repair_expected_text']=expected_after
    pending['repair_operation']=operation
    pending['repair_shape_id']=int(corrupt_shape.get('id') or 0)
    pending['repair_shape_text']=current_text
    pending['repair_shape_geometry']=dict(corrupt_shape.get('geometry') or {})
    pending['repair_target_cx']=cx
    pending['repair_target_cy']=cy
    pending['repair_plan']=list(repair_plan)
    pending['repair_sibling_signature']=_task091_other_shapes_signature(
        window_state,pending['slide'],pending['repair_shape_id'])
    pending['repair_verify_attempts']=0
    pending['verify_attempts']=0
    pending['stage']='repair-select-issued'
    pending['target'].update({
        'label':repaired_target['label'],'role':repaired_target['role'],
        'bbox':[repaired_target['x'],repaired_target['y'],2,2],
        'cx':cx,'cy':cy,'source':repaired_target['source'],
        'slide':repaired_target['slide'],
        'foreground_sha256':repaired_target['foreground_sha256'],
        'deck_sha256':repaired_target['deck_sha256'],
        'proof_sha256':repaired_target['proof_sha256']})
    command=f"pyautogui.doubleClick({cx}, {cy}, interval=0.08)"
    return {'action':'exec','command':command,'target':repaired_target,
            'plan':'Select the freshly observed signed textbox for exactly one atomic repair mutation; the next mutation is forbidden until this delta is persisted and verified.',
            'specialist_phase':'repair-select-pending-target'}


def next_091_specialist_action(instruction, active_application, observation, state, window_state=None):
    if not _task091_match(instruction):
        return None
    state['owned']=True
    state.setdefault('mode','TRANSIENT_WPS')
    state.setdefault('spatial_index',0)
    state.setdefault('target_retries',0)
    window_state=window_state if window_state is not None else _task091_window_state()

    # Synchronize trusted guest window state with a strictly bounded retry budget.
    if window_state is None:
        state['mode']='TRANSIENT_WPS'
        sync_retries=int(state.get('sync_window_retries') or 0)+1
        state['sync_window_retries']=sync_retries
        if sync_retries > 2:
            return _task091_terminal('TASK091_WINDOW_SYNC_EXHAUSTED',state)
        return {'action':'exec','command':"pyautogui.sleep(0.2)",
                'plan':'Synchronize trusted guest foreground state before any task action.',
                'specialist_phase':'sync-window-state'}
    state.pop('sync_window_retries',None)

    try:
        app=classify_wps_window(window_state.get('window',{}))
    except Exception:
        return _task091_terminal('WPS_DECK_FOREGROUND_UNPROVEN',state)
    window=window_state.get('window',{})
    title=str(window.get('title','')).strip().casefold()

    if app == 'wps-transient':
        state['mode']='TRANSIENT_WPS'
        pending=state.get('pending_edit')
        if isinstance(pending,dict):
            stage=str(pending.get('stage') or '')
            if stage in ('select-issued','table-select-issued','table-cell-enter-issued','reselect-required'):
                interrupts=int(pending.get('selection_interrupts') or 0)+1
                pending['selection_interrupts']=interrupts
                if interrupts > 3:
                    return _task091_terminal('TASK091_SELECTION_TRANSIENT_LOOP',state)
                pending['stage']='reselect-required'
                pending['selection_invalidated_by']=str(window.get('title') or 'wps-transient')
                pending.pop('selected_screenshot_sha256',None)
                pending.pop('selection_ack_foreground_sha256',None)
            elif stage in ('repair-select-issued','repair-reselect-required'):
                interrupts=int(pending.get('repair_selection_interrupts') or 0)+1
                pending['repair_selection_interrupts']=interrupts
                if interrupts > 3:
                    return _task091_terminal('TASK091_REPAIR_SELECTION_TRANSIENT_LOOP',state)
                pending['stage']='repair-reselect-required'
            elif stage in ('edit-issued','commit-issued','save-issued',
                           'repair-edit-issued','repair-commit-issued','repair-save-issued'):
                return _task091_terminal('TASK091_EDIT_INTERRUPTED_BY_TRANSIENT',state)
        current=state.get('transient_title')
        phase=state.get('transient_phase')
        if current != title:
            state['transient_title']=title
            state['transient_phase']=None
            phase=None
        if title == 'system check':
            if phase is None:
                state['transient_phase']='tab-issued'
                return {'action':'exec','command':"pyautogui.press('tab')",
                        'plan':'Focus the System Check Close control while retaining WPS transient ownership.',
                        'specialist_phase':'transient-system-check-tab'}
            if phase == 'tab-issued':
                state['transient_phase']='space-issued'
                return {'action':'exec','command':"pyautogui.press('space')",
                        'plan':'Activate the focused System Check Close button using its native button activation key.',
                        'specialist_phase':'transient-system-check-space'}
            if phase == 'space-issued':
                close,reason=_task091_system_check_close(window_state)
                if close is None:
                    return _task091_terminal(reason or 'WPS_TRANSIENT_CLOSE_UNPROVEN',state)
                state['transient_phase']='click-issued'
                command=f"pyautogui.click({int(close['cx'])}, {int(close['cy'])})"
                return {'action':'exec','command':command,
                        'target':{'source':'accessibility','label':'Close','role':close.get('role')},
                        'plan':'Fallback only to the unique guest-proven Close button inside the active System Check transient.',
                        'specialist_phase':'transient-system-check-verified-close-click'}
            return _task091_terminal('WPS_TRANSIENT_CLOSE_UNPROVEN',state)
        if title in ('wps office','set wps office as your default office software'):
            if phase is None:
                state['transient_phase']='esc-issued'
                return {'action':'exec','command':"pyautogui.press('esc')",
                        'plan':'Dismiss the allowlisted WPS default-office transient and re-probe foreground.',
                        'specialist_phase':'transient-default-office-esc'}
            return _task091_terminal('WPS_TRANSIENT_CLOSE_UNPROVEN',state)
        return _task091_terminal('WPS_TRANSIENT_CLOSE_UNPROVEN',state)

    if app != 'wps-presentation':
        return _task091_terminal('WPS_DECK_FOREGROUND_UNPROVEN',state)

    state['mode']='DECK_ACTIVE'
    state.pop('transient_phase',None)
    state.pop('transient_title',None)
    if not _task091_canvas_ready(observation,window_state):
        misses=int(state.get('deck_observation_retries') or 0)
        if misses>=1:
            return _task091_terminal('WPS_DECK_FOREGROUND_UNPROVEN',state)
        state['deck_observation_retries']=misses+1
        return {'action':'exec','command':"pyautogui.sleep(0.2)",
                'plan':'Deck foreground is proven by guest state; re-observe AT-SPI deck content once.',
                'specialist_phase':'deck-a11y-resync'}
    state['deck_observation_retries']=0

    if not state.get('anchored'):
        state['anchored']=True
        state['slide']=1
        return {'action':'exec','command':"pyautogui.hotkey('ctrl', 'home')",
                'plan':'Foreground is the official deck; anchor navigation at slide 1.',
                'specialist_phase':'anchor-slide-1'}

    pending=state.get('pending_edit')
    if isinstance(pending,dict):
        stage=pending.get('stage')
        state['mode']={'reselect-required':'TARGET_RESELECT_REQUIRED',
                       'select-issued':'TARGET_SELECTION_PENDING',
                       'table-select-issued':'TARGET_TABLE_SELECTED_PENDING',
                       'table-cell-enter-issued':'TARGET_CELL_TEXTMODE_PENDING',
                       'edit-issued':'TARGET_EDITING',
                       'commit-issued':'TARGET_COMMITTED','save-issued':'TARGET_VERIFYING',
                       'repair-reselect-required':'TARGET_RESELECT_REQUIRED',
                       'repair-select-issued':'TARGET_SELECTION_PENDING',
                       'repair-edit-issued':'TARGET_EDITING',
                       'repair-commit-issued':'TARGET_COMMITTED','repair-save-issued':'TARGET_VERIFYING'}.get(stage,'TARGET_VERIFYING')
        if stage == 'reselect-required':
            current_file=window_state.get('deck_file',{}) if isinstance(window_state,dict) else {}
            current_sha=str(current_file.get('sha256') or '') if isinstance(current_file,dict) else ''
            if current_sha != str(pending.get('before_deck_sha256') or ''):
                return _task091_terminal('TASK091_RESELECT_DECK_DRIFT',state)
            if int(window_state.get('active_slide') or 0) != int(pending.get('slide') or 0):
                return _task091_terminal('TASK091_RESELECT_SLIDE_DRIFT',state)
            shape=_task091_shape_by_id(window_state,pending['slide'],pending.get('shape_id'))
            if shape is None or _task091_norm(pending.get('old')) not in _task091_norm(shape.get('text')):
                return _task091_terminal('TASK091_RESELECT_SHAPE_DRIFT',state)
            recovery_attempt=int(pending.get('selection_recovery_attempts') or 0)
            if recovery_attempt:
                point=_task091_drift_safe_text_point(
                    window_state,shape,pending.get('text_hint_x'),pending.get('text_hint_y'),
                    recovery_attempt=recovery_attempt)
            else:
                point=_task091_shape_point(window_state,pending['slide'],pending['old'],
                                           pending.get('text_hint_x'),pending.get('text_hint_y'))
            if point is None or int(point['shape'].get('id') or 0) != int(pending.get('shape_id') or 0):
                return _task091_terminal('TASK091_RESELECT_GEOMETRY_UNPROVEN',state)
            cx=int(point['cx']); cy=int(point['cy'])
            target={'source':'task091-pptx-canonical','label':pending['old'],
                    'role':'task091-canonical-point','slide':int(pending['slide']),
                    'x':cx-1,'y':cy-1,'w':2,'h':2,'cx':cx,'cy':cy,
                    'foreground_sha256':_task091_foreground_sha(window_state),
                    'deck_sha256':current_sha}
            target['proof_sha256']=task091_spatial_target_proof(target)
            pending['target'].update({
                'label':target['label'],'role':target['role'],
                'bbox':[target['x'],target['y'],target['w'],target['h']],
                'cx':cx,'cy':cy,'source':target['source'],'slide':target['slide'],
                'foreground_sha256':target['foreground_sha256'],
                'deck_sha256':target['deck_sha256'],'proof_sha256':target['proof_sha256']})
            pending['text_hit_x']=cx
            pending['text_hit_y']=cy
            pending['selection_before_screenshot_sha256']=str(window_state.get('screenshot_sha256') or '')
            pending['selection_foreground_sha256']=target['foreground_sha256']
            is_table_cell=str(shape.get('kind') or '') == 'table-cell'
            pending['stage']='table-select-issued' if is_table_cell else 'select-issued'
            command=(f"pyautogui.click({cx}, {cy})" if is_table_cell
                     else f"pyautogui.doubleClick({cx}, {cy}, interval=0.08)")
            pending['selection_command_hash']=hashlib.sha256(command.encode()).hexdigest()
            return {'action':'exec','command':command,
                    'target':target,
                    'plan':('Re-select the exact table cell container before a separately observed text-entry click.'
                            if is_table_cell else
                            'Re-select the exact PPTX shape after transient invalidated the previous unacknowledged selection.'),
                    'specialist_phase':('table-reselect-container' if is_table_cell else 'reselect-pending-target')}
        if stage == 'table-select-issued':
            current_file=window_state.get('deck_file',{}) if isinstance(window_state,dict) else {}
            current_sha=str(current_file.get('sha256') or '') if isinstance(current_file,dict) else ''
            current_fg=_task091_foreground_sha(window_state)
            current_shot=str(window_state.get('screenshot_sha256') or '')
            before_shot=str(pending.get('selection_before_screenshot_sha256') or pending.get('before_screenshot_sha256') or '')
            shape=_task091_shape_by_id(window_state,pending['slide'],pending.get('shape_id'))
            siblings=_task091_other_shapes_signature(window_state,pending['slide'],pending.get('shape_id'))
            frame_id=int(shape.get('frame_id') or 0) if isinstance(shape,dict) else 0
            target_visual=_task091_region_sha256(window_state,list(pending.get('shape_bbox') or []))
            sibling_visual=_task091_table_visual_signature(
                window_state,pending['slide'],frame_id,pending.get('shape_id'))
            ack=(current_sha == str(pending.get('before_deck_sha256') or '')
                 and int(window_state.get('active_slide') or 0) == int(pending.get('slide') or 0)
                 and shape is not None
                 and str(shape.get('kind') or '') == 'table-cell'
                 and str(shape.get('text') or '') == str(pending.get('old') or '')
                 and siblings == str(pending.get('before_sibling_signature') or '')
                 and len(current_fg)==64
                 and current_fg == str(pending.get('selection_foreground_sha256') or '')
                 and len(current_shot)==64 and len(before_shot)==64 and current_shot != before_shot
                 and len(target_visual)==64 and len(sibling_visual)==64)
            if not ack:
                return _task091_terminal('TASK091_TABLE_SELECTION_NOT_ACKNOWLEDGED',state)
            pending['table_selected_screenshot_sha256']=current_shot
            pending['table_selected_source']=str(window_state.get('source') or '')
            pending['table_selected_sibling_signature']=siblings
            pending['table_frame_id']=frame_id
            pending['table_selected_target_visual_sha256']=target_visual
            pending['table_selected_sibling_visual_sha256']=sibling_visual
            text_ink=_task091_table_cell_text_ink_point(
                window_state,list(pending.get('shape_bbox') or []))
            if text_ink is None:
                return _task091_terminal('TASK091_TABLE_TEXT_INK_UNPROVEN',state)
            pending['table_text_hit_x']=int(text_ink['cx'])
            pending['table_text_hit_y']=int(text_ink['cy'])
            pending['table_text_ink_bbox']=list(text_ink['ink_bbox'])
            pending['table_text_ink_pixels']=int(text_ink['ink_pixels'])
            pending['table_text_ink_proof_sha256']=str(text_ink['proof_sha256'])
            pending['table_text_ink_source']=str(text_ink['source'])
            pending['stage']='table-cell-text-hit-issued'
            pending['textmode_baseline_source']=str(window_state.get('source') or '')
            cx=int(text_ink['cx']); cy=int(text_ink['cy'])
            command=f"pyautogui.click({cx}, {cy})"
            pending['cell_text_hit_command_hash']=hashlib.sha256(command.encode()).hexdigest()
            stored=pending.get('target') if isinstance(pending.get('target'),dict) else {}
            action_target={'source':'task091-pptx-canonical','label':stored.get('label'),
                           'role':stored.get('role'),'slide':stored.get('slide'),
                           'x':cx-1,'y':cy-1,'w':2,'h':2,'cx':cx,'cy':cy,
                           'foreground_sha256':stored.get('foreground_sha256'),
                           'deck_sha256':stored.get('deck_sha256')}
            action_target['proof_sha256']=task091_spatial_target_proof(action_target)
            pending['table_text_action_proof_sha256']=action_target['proof_sha256']
            return {'action':'exec','command':command,
                    'target':action_target,
                    'plan':'The exact table container is selected; click the raster-proven text ink point once, re-observe all invariants, then issue one separately audited text-mode click. No text mutation is allowed yet.',
                    'specialist_phase':'table-cell-text-hit-candidate'}
        if stage == 'table-cell-text-hit-issued':
            current_file=window_state.get('deck_file',{}) if isinstance(window_state,dict) else {}
            current_sha=str(current_file.get('sha256') or '') if isinstance(current_file,dict) else ''
            current_fg=_task091_foreground_sha(window_state)
            shape=_task091_shape_by_id(window_state,pending['slide'],pending.get('shape_id'))
            siblings=_task091_other_shapes_signature(window_state,pending['slide'],pending.get('shape_id'))
            sibling_visual=_task091_table_visual_signature(
                window_state,pending['slide'],pending.get('table_frame_id'),pending.get('shape_id'))
            safe=(current_sha == str(pending.get('before_deck_sha256') or '')
                  and int(window_state.get('active_slide') or 0) == int(pending.get('slide') or 0)
                  and shape is not None
                  and str(shape.get('kind') or '') == 'table-cell'
                  and str(shape.get('text') or '') == str(pending.get('old') or '')
                  and siblings == str(pending.get('before_sibling_signature') or '')
                  and siblings == str(pending.get('table_selected_sibling_signature') or '')
                  and len(current_fg)==64
                  and current_fg == str(pending.get('selection_foreground_sha256') or '')
                  and len(sibling_visual)==64
                  and sibling_visual == str(pending.get('table_selected_sibling_visual_sha256') or '')
                  and len(str(pending.get('table_text_ink_proof_sha256') or ''))==64
                  and len(str(pending.get('cell_text_hit_command_hash') or ''))==64)
            if not safe:
                return _task091_terminal('TASK091_TABLE_TEXT_HIT_DRIFT',state)
            source=str(window_state.get('source') or '')
            baseline=str(pending.get('textmode_baseline_source') or '')
            if (not re.fullmatch(r'\d{4}-\d{2}-(?:before|after)',source)
                    or not re.fullmatch(r'\d{4}-\d{2}-(?:before|after)',baseline)):
                return _task091_terminal('TASK091_TABLE_TEXTMODE_EVIDENCE_MISSING',state)
            cx=int(pending.get('table_text_hit_x') or 0); cy=int(pending.get('table_text_hit_y') or 0)
            if cx<=0 or cy<=0:
                return _task091_terminal('TASK091_TABLE_TEXT_HIT_GEOMETRY_UNPROVEN',state)
            pending['stage']='table-cell-enter-issued'
            pending['textmode_first_hit_source']=source
            command=f"pyautogui.click({cx}, {cy})"
            pending['cell_enter_command_hash']=hashlib.sha256(command.encode()).hexdigest()
            stored=pending.get('target') if isinstance(pending.get('target'),dict) else {}
            action_target={'source':'task091-pptx-canonical','label':stored.get('label'),
                           'role':stored.get('role'),'slide':stored.get('slide'),
                           'x':cx-1,'y':cy-1,'w':2,'h':2,'cx':cx,'cy':cy,
                           'foreground_sha256':stored.get('foreground_sha256'),
                           'deck_sha256':stored.get('deck_sha256')}
            action_target['proof_sha256']=task091_spatial_target_proof(action_target)
            return {'action':'exec','command':command,'target':action_target,
                    'plan':'The first raster-proven text hit preserved every deck/table invariant. Issue exactly one separately observed second click at the same signed ink point, then prove text mode against the immutable pre-hit baseline.',
                    'specialist_phase':'enter-table-cell-caret-candidate'}
        if stage in ('table-cell-enter-issued','table-cell-caret-probe-issued'):
            current_file=window_state.get('deck_file',{}) if isinstance(window_state,dict) else {}
            current_sha=str(current_file.get('sha256') or '') if isinstance(current_file,dict) else ''
            current_fg=_task091_foreground_sha(window_state)
            shape=_task091_shape_by_id(window_state,pending['slide'],pending.get('shape_id'))
            siblings=_task091_other_shapes_signature(window_state,pending['slide'],pending.get('shape_id'))
            sibling_visual=_task091_table_visual_signature(
                window_state,pending['slide'],pending.get('table_frame_id'),pending.get('shape_id'))
            bbox=list(pending.get('shape_bbox') or [])
            baseline=str(pending.get('textmode_baseline_source') or '')
            caret=_task091_caret_delta_geometry(baseline,window_state.get('source'),bbox)
            safe=(current_sha == str(pending.get('before_deck_sha256') or '')
                  and int(window_state.get('active_slide') or 0) == int(pending.get('slide') or 0)
                  and shape is not None
                  and str(shape.get('kind') or '') == 'table-cell'
                  and str(shape.get('text') or '') == str(pending.get('old') or '')
                  and siblings == str(pending.get('before_sibling_signature') or '')
                  and siblings == str(pending.get('table_selected_sibling_signature') or '')
                  and len(current_fg)==64
                  and current_fg == str(pending.get('selection_foreground_sha256') or '')
                  and len(sibling_visual)==64
                  and sibling_visual == str(pending.get('table_selected_sibling_visual_sha256') or '')
                  and len(str(pending.get('table_text_ink_proof_sha256') or ''))==64
                  and len(str(pending.get('cell_enter_command_hash') or ''))==64
                  and re.fullmatch(r'\d{4}-\d{2}-(?:before|after)',baseline) is not None)
            if not safe:
                return _task091_terminal('TASK091_TABLE_CELL_ENTRY_DRIFT',state)
            pending['caret_geometry']=caret
            pending['caret_baseline_source']=baseline
            pending['caret_observed_source']=str(window_state.get('source') or '')
            if caret.get('proven') is not True:
                attempts=int(pending.get('caret_probe_attempts') or 0)
                source=str(window_state.get('source') or '')
                if not re.fullmatch(r'\d{4}-\d{2}-(?:before|after)',source):
                    return _task091_terminal('TASK091_TABLE_CELL_CARET_EVIDENCE_MISSING',state)
                if attempts >= 4:
                    return _task091_terminal('TASK091_TABLE_CELL_CARET_GEOMETRY_UNPROVEN',state)
                pending['caret_probe_attempts']=attempts+1
                pending['stage']='table-cell-caret-probe-issued'
                delay=(0.30,0.55,0.80,1.05)[attempts]
                command=f"pyautogui.sleep({delay:.2f})"
                pending['caret_probe_command_hash']=hashlib.sha256(command.encode()).hexdigest()
                return {'action':'exec','command':command,
                        'plan':'Sample the unchanged signed cell against the immutable pre-text-mode baseline. Mutation remains forbidden until narrow caret geometry is positively proven.',
                        'specialist_phase':f'table-cell-caret-baseline-probe-{attempts+1}'}
            pending['selected_screenshot_sha256']=str(window_state.get('screenshot_sha256') or '')
            pending['selection_ack_foreground_sha256']=current_fg
            pending['explicit_text_mode']=True
            pending['stage']='edit-issued'
            command=_task091_table_cell_bounded_write_command(pending['old'],pending['new'])
            pending['action_command_hash']=hashlib.sha256(command.encode()).hexdigest()
            return {'action':'exec','command':command,
                    'plan':f"Replace only the geometrically proven table-cell caret target {pending['old']!r} using End + bounded Backspace + write; Ctrl+A is forbidden.",
                    'specialist_phase':'edit-geometry-proven-table-cell','expected_change':pending['new']}
        if stage == 'select-issued':
            current_file=window_state.get('deck_file',{}) if isinstance(window_state,dict) else {}
            current_sha=str(current_file.get('sha256') or '') if isinstance(current_file,dict) else ''
            current_fg=_task091_foreground_sha(window_state)
            current_shot=str(window_state.get('screenshot_sha256') or '')
            expected_fg=str(pending.get('selection_foreground_sha256') or pending.get('target',{}).get('foreground_sha256') or '')
            before_shot=str(pending.get('selection_before_screenshot_sha256') or pending.get('before_screenshot_sha256') or '')
            shape=_task091_shape_by_id(window_state,pending['slide'],pending.get('shape_id'))
            ack=(current_sha == str(pending.get('before_deck_sha256') or '')
                 and int(window_state.get('active_slide') or 0) == int(pending.get('slide') or 0)
                 and shape is not None
                 and _task091_norm(pending.get('old')) in _task091_norm(shape.get('text'))
                 and len(current_fg)==64 and current_fg == expected_fg
                 and len(current_shot)==64 and len(before_shot)==64 and current_shot != before_shot)
            if not ack:
                attempts=int(pending.get('selection_ack_attempts') or 0)+1
                pending['selection_ack_attempts']=attempts
                if attempts >= 2:
                    return _task091_terminal('TASK091_SELECTION_NOT_ACKNOWLEDGED',state)
                pending['stage']='reselect-required'
                return {'action':'exec','command':"pyautogui.sleep(0.2)",
                        'plan':'Selection was not positively acknowledged in the same deck/slide/shape; re-observe before reselecting.',
                        'specialist_phase':'reobserve-unacknowledged-selection'}
            pending['selected_screenshot_sha256']=current_shot
            pending['selection_ack_foreground_sha256']=current_fg
            pending['stage']='edit-issued'
            pending['explicit_text_mode']=True
            command=_task091_write_command(pending['new'], ensure_text_mode=False)
            pending['action_command_hash']=hashlib.sha256(command.encode()).hexdigest()
            return {'action':'exec','command':command,
                    'plan':f"Edit the positively acknowledged target from {pending['old']!r} to {pending['new']!r}.",
                    'specialist_phase':'edit-pending-target','expected_change':pending['new']}
        if stage == 'edit-issued':
            pending['edited_screenshot_sha256']=str(window_state.get('screenshot_sha256') or '')
            pending['stage']='commit-issued'
            command="pyautogui.press('esc')"
            pending['commit_command_hash']=hashlib.sha256(command.encode()).hexdigest()
            return {'action':'exec','command':command,
                    'plan':'Commit the pending shape edit without advancing its transaction.',
                    'specialist_phase':'commit-pending-target','expected_change':pending['new']}
        if stage == 'repair-reselect-required':
            shape=_task091_shape_by_id(window_state,pending['slide'],pending.get('repair_shape_id'))
            if shape is None or str(shape.get('text') or '') != str(pending.get('repair_before_text') or ''):
                return _task091_terminal('TASK091_REPAIR_RESELECT_PROOF_DRIFT',state)
            repair_point=_task091_shape_text_point(window_state,shape,
                                                   pending.get('repair_target_cx'),
                                                   pending.get('repair_target_cy'))
            if repair_point is None:
                return _task091_terminal('TASK091_REPAIR_RESELECT_GEOMETRY_UNPROVEN',state)
            cx=int(repair_point['cx']); cy=int(repair_point['cy'])
            pending['repair_selection_before_screenshot_sha256']=str(window_state.get('screenshot_sha256') or '')
            pending['stage']='repair-select-issued'
            command=f"pyautogui.doubleClick({cx}, {cy}, interval=0.08)"
            pending['repair_selection_command_hash']=hashlib.sha256(command.encode()).hexdigest()
            return {'action':'exec','command':command,
                    'plan':'Re-select the freshly proven repair textbox after transient invalidated the prior selection.',
                    'specialist_phase':'repair-reselect-pending-target'}
        if stage == 'repair-select-issued':
            pending['repair_selected_screenshot_sha256']=str(window_state.get('screenshot_sha256') or '')
            shape=_task091_shape_by_id(window_state,pending['slide'],pending.get('repair_shape_id'))
            if shape is None or str(shape.get('text') or '') != str(pending.get('repair_before_text') or ''):
                return _task091_terminal('TASK091_RESTRICTED_REPAIR_PROOF_DRIFT',state)
            if _task091_other_shapes_signature(window_state,pending['slide'],pending.get('repair_shape_id')) != str(pending.get('repair_sibling_signature') or ''):
                return _task091_terminal('TASK091_RESTRICTED_REPAIR_SIBLING_DRIFT',state)
            repair_plan=_task091_restricted_repair_plan(str(shape.get('text') or ''),pending['new'])
            operation=dict(pending.get('repair_operation') or {})
            if not repair_plan or dict(repair_plan[0]) != operation:
                return _task091_terminal('TASK091_RESTRICTED_REPAIR_PROOF_DRIFT',state)
            pending['stage']='repair-edit-issued'
            command=_task091_restricted_repair_command([operation])
            pending['repair_action_command_hash']=hashlib.sha256(command.encode()).hexdigest()
            return {'action':'exec','command':command,
                    'plan':'Apply exactly one freshly proven repair mutation from a deterministic text origin; no second destructive mutation is allowed in this action.',
                    'specialist_phase':'repair-atomic-pending-target','expected_change':pending['repair_expected_text']}
        if stage == 'repair-edit-issued':
            pending['repair_edited_screenshot_sha256']=str(window_state.get('screenshot_sha256') or '')
            pending['stage']='repair-commit-issued'
            command="pyautogui.press('esc')"
            pending['repair_commit_command_hash']=hashlib.sha256(command.encode()).hexdigest()
            return {'action':'exec','command':command,
                    'plan':'Commit the one-operation repair without issuing any further text mutation.',
                    'specialist_phase':'repair-commit-pending-target','expected_change':pending['repair_expected_text']}
        if stage == 'repair-commit-issued':
            pending['stage']='repair-save-issued'
            command="pyautogui.hotkey('ctrl', 's')\npyautogui.sleep(0.25)"
            pending['repair_save_command_hash']=hashlib.sha256(command.encode()).hexdigest()
            return {'action':'exec','command':command,
                    'plan':'Persist exactly one repair mutation before any replan is permitted.',
                    'specialist_phase':'repair-save-pending-target','expected_change':pending['repair_expected_text']}
        if stage == 'repair-save-issued':
            current_file=window_state.get('deck_file',{}) if isinstance(window_state,dict) else {}
            after_sha=str(current_file.get('sha256') or '') if isinstance(current_file,dict) else ''
            before_sha=str(pending.get('repair_before_deck_sha256') or '')
            if len(after_sha)!=64 or len(before_sha)!=64:
                return _task091_terminal('TASK091_REPAIR_PERSISTENCE_UNPROVEN',state)
            if after_sha == before_sha:
                attempts=int(pending.get('repair_verify_attempts') or 0)+1
                pending['repair_verify_attempts']=attempts
                if attempts>=2:
                    return _task091_terminal('TASK091_REPAIR_NOT_PERSISTED',state)
                return {'action':'exec','command':"pyautogui.sleep(0.2)",
                        'plan':'The atomic repair save is not visible on disk yet; re-observe without any destructive input.',
                        'specialist_phase':'repair-reobserve-pending-target'}
            shape=_task091_shape_by_id(window_state,pending['slide'],pending.get('repair_shape_id'))
            if shape is None:
                return _task091_terminal('TASK091_REPAIR_DELTA_MISMATCH',state)
            actual_text=str(shape.get('text') or '')
            expected_text=str(pending.get('repair_expected_text') or '')
            if actual_text != expected_text:
                return _task091_terminal('TASK091_REPAIR_DELTA_MISMATCH',state)
            if _task091_other_shapes_signature(window_state,pending['slide'],pending.get('repair_shape_id')) != str(pending.get('repair_sibling_signature') or ''):
                return _task091_terminal('TASK091_REPAIR_SIBLING_MUTATION',state)
            pending['repair_verify_attempts']=0
            if actual_text == str(pending.get('new') or ''):
                verified,status,new_hit=_task091_verify_pending(observation,pending,window_state)
                if not verified:
                    return _task091_terminal('TASK091_REPAIR_FINAL_PROOF_MISMATCH',state)
                state['mode']='TARGET_VERIFIED'
                state['spatial_index']=int(state.get('spatial_index') or 0)+1
                state['pending_edit']=None
                state['target_retries']=0
                checkpoint='TASK091_FIRST_STRUCTURAL_EDIT_VERIFIED' if state['spatial_index']==1 else 'TASK091_STRUCTURAL_EDIT_VERIFIED'
                if state['spatial_index']==1:
                    state['first_structural_edit_verified']=True
                return {'action':'checkpoint','checkpoint':checkpoint,
                        'slide':pending['slide'],'old':pending['old'],'new':pending['new'],
                        'target':new_hit,'specialist_phase':'verify-atomic-repair-target'}
            return _task091_prepare_atomic_repair(pending,window_state,state)
        if stage == 'commit-issued':
            pending['stage']='save-issued'
            command="pyautogui.hotkey('ctrl', 's')\npyautogui.sleep(0.25)"
            pending['save_command_hash']=hashlib.sha256(command.encode()).hexdigest()
            return {'action':'exec','command':command,
                    'plan':'Persist the pending GUI edit before verifying the target PPTX on disk.',
                    'specialist_phase':'save-pending-target','expected_change':pending['new']}
        if stage == 'save-issued':
            verified,status,new_hit=_task091_verify_pending(observation,pending,window_state)
            if verified:
                state['mode']='TARGET_VERIFIED'
                state['spatial_index']=int(state.get('spatial_index') or 0)+1
                state['pending_edit']=None
                state['target_retries']=0
                checkpoint='TASK091_FIRST_STRUCTURAL_EDIT_VERIFIED' if state['spatial_index']==1 else 'TASK091_STRUCTURAL_EDIT_VERIFIED'
                if state['spatial_index']==1:
                    state['first_structural_edit_verified']=True
                return {'action':'checkpoint','checkpoint':checkpoint,
                        'slide':pending['slide'],'old':pending['old'],'new':pending['new'],
                        'target':new_hit,'specialist_phase':'verify-pending-target'}
            if status=='collateral-mutation':
                return _task091_terminal('TASK091_COLLATERAL_EDIT_DETECTED',state)
            if status=='disk-text-mismatch' and int(pending.get('repair_steps') or pending.get('repair_attempts') or 0)==0:
                selected=str(pending.get('selected_screenshot_sha256') or '')
                edited=str(pending.get('edited_screenshot_sha256') or '')
                visual_edit_proven=(len(selected)==64 and len(edited)==64 and selected != edited)
                if not visual_edit_proven:
                    return _task091_terminal('TASK091_EDIT_TEXT_MISMATCH_UNPROVEN',state)
                return _task091_prepare_atomic_repair(pending,window_state,state)
            attempts=int(pending.get('verify_attempts') or 0)+1
            pending['verify_attempts']=attempts
            if attempts>=2:
                current_file=window_state.get('deck_file',{}) if isinstance(window_state,dict) else {}
                current_sha=str(current_file.get('sha256') or '') if isinstance(current_file,dict) else ''
                expected_shape=_task091_shape_by_id(window_state,pending['slide'],pending.get('shape_id'))
                unchanged_target=(len(current_sha)==64
                                  and current_sha==str(pending.get('before_deck_sha256') or '')
                                  and isinstance(expected_shape,dict)
                                  and str(expected_shape.get('text') or '')==str(pending.get('old') or ''))
                if status!='disk-text-mismatch' and unchanged_target:
                    recoveries=int(pending.get('selection_recovery_attempts') or 0)
                    if recoveries>=2:
                        return _task091_terminal('TASK091_TEXT_SELECTION_UNPROVEN',state)
                    pending['selection_recovery_attempts']=recoveries+1
                    pending['selection_ack_attempts']=0
                    pending['verify_attempts']=0
                    pending['stage']='reselect-required'
                    pending.pop('selected_screenshot_sha256',None)
                    pending.pop('selection_ack_foreground_sha256',None)
                    return {'action':'exec','command':"pyautogui.sleep(0.2)",
                            'plan':'The deck and exact target text stayed unchanged after save; invalidate the visual-only selection ACK and retry a bounded interior text hit.',
                            'specialist_phase':'recover-nonpersisted-text-selection'}
                reason='TASK091_EDIT_TEXT_CORRUPTED' if status=='disk-text-mismatch' else 'TASK091_EDIT_NOT_VERIFIED'
                return _task091_terminal(reason,state)
            return {'action':'exec','command':"pyautogui.sleep(0.2)",
                    'plan':'Pending edit is not semantically verified yet; re-observe same target without advancing.',
                    'specialist_phase':'reobserve-pending-target'}
        return _task091_terminal('TASK091_EDIT_NOT_COMMITTED',state)

    index=int(state.get('spatial_index') or 0)
    if index < len(TASK091_SPATIAL_TEXT_EDITS):
        slide,x,y,old,new=TASK091_SPATIAL_TEXT_EDITS[index]
        current=int(state.get('slide') or 1)
        nav=_task091_nav_command(current,slide)
        if nav:
            state['slide']=slide
            return {'action':'exec','command':nav,
                    'plan':f'Navigate from slide {current} to slide {slide} before editing {old!r}.',
                    'specialist_phase':'navigate-slide'}

        if _task091_norm(old) == _task091_norm(new):
            state['spatial_index']=index+1
            state['mode']='TARGET_VERIFIED'
            return {'action':'checkpoint','checkpoint':'TASK091_TARGET_ALREADY_FINAL',
                    'slide':slide,'old':old,'new':new,
                    'target':{'source':'task091-final-state','x':x,'y':y},
                    'specialist_phase':'skip-already-final-target'}

        before_old=_task091_text_count(window_state,slide,old)
        before_new=_task091_text_count(window_state,slide,new)
        shape_target=_task091_shape_point(window_state,slide,old,x,y)
        if shape_target is None:
            retries=int(state.get('target_retries') or 0)
            if retries<1:
                state['target_retries']=retries+1
                return {'action':'exec','command':"pyautogui.sleep(0.2)",
                        'plan':f'Re-observe exact PPTX shape geometry once for {old!r}.',
                        'specialist_phase':'reobserve-shape-geometry'}
            return _task091_terminal('TASK091_SHAPE_GEOMETRY_UNPROVEN',state)
        source='task091-pptx-canonical'
        shape=shape_target['shape']
        text_hint_x=int(x); text_hint_y=int(y)
        x=int(shape_target['cx']); y=int(shape_target['cy'])
        target={'source':source,'label':old,'role':'task091-canonical-point',
                'slide':int(slide),'x':x-1,'y':y-1,'w':2,'h':2,
                'cx':x,'cy':y,
                'foreground_sha256':_task091_foreground_sha(window_state),
                'deck_sha256':str((window_state.get('deck_file',{}) or {}).get('sha256',''))}
        target['proof_sha256']=task091_spatial_target_proof(target)

        state['target_retries']=0
        state['mode']='TARGET_VISIBLE'
        is_table_cell=str(shape.get('kind') or '') == 'table-cell'
        command=(f"pyautogui.click({int(target['cx'])}, {int(target['cy'])})"
                 if is_table_cell else
                 f"pyautogui.doubleClick({int(target['cx'])}, {int(target['cy'])}, interval=0.08)")
        state['pending_edit']={
            'slide':slide,'old':old,'new':new,
            'stage':('table-select-issued' if is_table_cell else 'select-issued'),
            'target':{'label':target['label'],'role':target['role'],
                      'bbox':[target['x'],target['y'],target['w'],target['h']],
                      'cx':target['cx'],'cy':target['cy'],'source':source,
                      'slide':target.get('slide'),'foreground_sha256':target.get('foreground_sha256'),
                      'deck_sha256':target.get('deck_sha256'),'proof_sha256':target.get('proof_sha256')},
            'shape_id':int(shape.get('id') or 0),
            'shape_name':str(shape.get('name') or ''),
            'shape_kind':str(shape.get('kind') or ''),
            'shape_geometry':dict(shape.get('geometry') or {}),
            'shape_bbox':list(shape_target.get('shape_bbox') or []),
            'shape_center_cx':shape_target.get('shape_center_cx'),
            'shape_center_cy':shape_target.get('shape_center_cy'),
            'text_hit_x':target['cx'],'text_hit_y':target['cy'],
            'text_hint_x':text_hint_x,'text_hint_y':text_hint_y,
            'before_old_count':before_old,'before_new_count':before_new,
            'before_deck_sha256':str((window_state.get('deck_file',{}) or {}).get('sha256','')),
            'before_screenshot_sha256':str(window_state.get('screenshot_sha256') or ''),
            'before_sibling_signature':_task091_other_shapes_signature(window_state,slide,int(shape.get('id') or 0)),
            'selection_before_screenshot_sha256':str(window_state.get('screenshot_sha256') or ''),
            'selection_foreground_sha256':_task091_foreground_sha(window_state),
            'selection_ack_attempts':0,
            'selection_interrupts':0,
            'selection_recovery_attempts':0,
            'before_observation_hash':hashlib.sha256(str(observation or '').encode()).hexdigest(),
            'action_command_hash':hashlib.sha256(command.encode()).hexdigest(),
            'verify_attempts':0,
        }
        action_target={'source':source,'label':target['label'],'role':target['role']}
        if source=='task091-pptx-canonical':
            action_target.update({key:target[key] for key in
                                  ('slide','x','y','w','h','cx','cy','foreground_sha256',
                                   'deck_sha256','proof_sha256')})
        return {'action':'exec','command':command,
                'target':action_target,
                'plan':(f'Select the exact table containing {old!r}; text entry requires a second separately observed cell click.'
                        if is_table_cell else
                        f'Activate the signed Task 091 point using unique target-PPTX shape geometry for {old!r} on slide {slide}.'),
                'specialist_phase':('select-table-container' if is_table_cell else 'select-pending-target')}

    if state.get('pending_edit'):
        return _task091_terminal('TASK091_EDIT_NOT_COMMITTED',state)
    if not state.get('saved'):
        state['saved']=True
        return {'action':'exec','command':"pyautogui.hotkey('ctrl', 's')\npyautogui.sleep(1)",
                'plan':'Save all semantically verified direct-object edits before structural chart/fill handoff.',
                'specialist_phase':'save-verified-spatial-pass'}
    state['mode']='STRUCTURAL_HANDOFF'
    state['handoff']=True
    state['handoff_reason']='DIRECT_TEXT_PASS_VERIFIED_CHART_FILL_REMAINS'
    return None

def try_091_specialist(body, obs, focused_obs):
    state=STATE.setdefault('task091_specialist',{})
    window_state=_task091_window_state()
    candidate=None
    for _ in range(3):
        candidate=next_091_specialist_action(
            body.get('instruction',''),body.get('active_application','unknown'),
            focused_obs,state,window_state)
        if not candidate:
            if state.get('owned') and not state.get('handoff'):
                return terminal(state.get('terminal_reason') or state.get('handoff_reason') or 'TASK091_TARGET_NOT_VISIBLE')
            return None
        if candidate.get('action')=='terminal':
            log_event({'status':'TASK091_SPECIALIST_TERMINAL','reason':candidate.get('reason'),
                       'mode':state.get('mode'),'pending_edit':state.get('pending_edit')})
            return terminal(candidate.get('reason') or 'TASK091_EDIT_NOT_VERIFIED')
        if candidate.get('action')=='checkpoint':
            log_event({'status':candidate.get('checkpoint'),'slide':candidate.get('slide'),
                       'old':candidate.get('old'),'new':candidate.get('new'),
                       'target':candidate.get('target'),'mode':state.get('mode'),
                       'spatial_index':state.get('spatial_index')})
            continue
        break
    if not candidate:
        return None
    try:
        action=ground_action(candidate,body.get('active_application','unknown'),focused_obs,body.get('verified_milestones',[]),
                             allow_canonical=True,verifier_result=VERIFIER.last_result,
                             recent_commands=[x['command'] for x in STATE['history'][-6:]])
        decision=apply_live_policy(action,body.get('active_application','unknown'),focused_obs,body.get('verified_milestones',[]))
        senior_review=require_senior_elite(
            action,task_id=os.environ.get('TASK_ID'),source='task091-specialist',
            state=STATE,verifier=VERIFIER.last_result,
            recent_commands=[x['command'] for x in STATE['history'][-6:]])
        log_event({'status':'SENIOR_ELITE_BOARD_PASS','source':'task091-specialist',
                   'pass':senior_review['pass'],'total':senior_review['total'],
                   'lanes':senior_review['lanes']})
    except ValueError as exc:
        log_event({'status':'TASK091_SPECIALIST_POLICY_REJECTED','reason':str(exc),'action':candidate,
                   'mode':state.get('mode'),'pending_edit':state.get('pending_edit')})
        return terminal('TASK091_SPECIALIST_POLICY_REJECTED:'+str(exc))
    if decision.get('kind')!=DecisionKind.EXEC.value or action.get('action')!='exec':
        return terminal('TASK091_SPECIALIST_NON_EXEC_DECISION')
    command=action['command']; STATE['plan']=str(action.get('plan') or STATE['plan'])[:1400]
    STATE['previous']=command; STATE['executed']+=1; STATE['wait_responses']=0; STATE['provider_waits']=0
    STATE['history'].append({'command':command,'expected':action.get('expected_change',''),'source':'task091-specialist'})
    STATE['history']=STATE['history'][-12:]; VERIFIER.issued(command)
    log_event({'status':'TASK091_SPECIALIST_ACTION_ISSUED','command':command,
               'phase':action.get('specialist_phase'),'mode':state.get('mode'),
               'spatial_index':state.get('spatial_index'),'pending_edit':state.get('pending_edit'),
               'window_state':window_state})
    log_event({'status':'ACTION_ISSUED','command':command,'source':'task091-specialist'})
    fence=chr(96)*3
    return fence+'python\n'+command+'\n'+fence


UPSTREAM = 'https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v5'
EXPECTED_PIPELINE = 'arbm-osworld-v32-isolated'
EXPECTED_BUILD = 'arbm-osworld-v32-master-20260914'
MAX_NO_PROGRESS = int(os.environ.get('ARBM_MAX_NO_PROGRESS', '12'))
MAX_WAIT_RESPONSES = int(os.environ.get('ARBM_MAX_WAIT_RESPONSES', '4'))
MAX_PROVIDER_WAIT_RESPONSES = int(os.environ.get('ARBM_MAX_PROVIDER_WAIT_RESPONSES', '24'))
MAX_STEPS = int(os.environ.get('ARBM_MAX_STEPS', '160'))
LOG = os.environ.get('ARBM_OSWORLD_SHIM_LOG', 'osworld-v32-shim.log')
OBS_DIR = Path(os.environ.get('ARBM_OSWORLD_OBSERVATIONS', 'shim-observations'))
LOCK = threading.Lock()
LOCAL_FALLBACK_CAPACITY_STATUSES = {
    'NO_ZERO_SPEND_MULTIMODAL_CAPACITY',
    'FREE_QUOTA_EXHAUSTED',
}
LOCAL_CONTRACT_STATUSES = {'LOCAL_ACTION_UNAVAILABLE','LOCAL_ACTION_CONTRACT_EXHAUSTED'}
STATE = {'step':0,'previous':'','executed':0,'phase':'plan','plan':'','memory':[],
         'history':[],'facts':[],'wait_responses':0,'provider_waits':0,'cooldowns':{},'terminal':'','provider':'','model':'','visual_memory':'','visual_memory_meta':None,'gimp_specialist':{}}
VERIFIER = Verifier()
MILESTONES = Milestones()
ELITE = EliteController(
    fast_latency_s=float(os.environ.get('ARBM_ELITE_FAST_LATENCY_S','8')),
    hard_latency_s=float(os.environ.get('ARBM_ELITE_HARD_LATENCY_S','20')),
    max_waits=int(os.environ.get('ARBM_ELITE_MAX_WAITS','2')),
    max_stall=int(os.environ.get('ARBM_ELITE_MAX_STALL','3')))
STARTED = time.monotonic()
MAX_TASK_SECONDS = int(os.environ.get('ARBM_TASK_SECONDS', '2400'))
HEALTH = {'last_event':'initializing','last_error':'','retry':0,'pending_since':None}
STOP = threading.Event()


# ARBM_TOP3_MESH_SESSION_BUDGET_V1
MESH_TOTAL_BUDGET_SECONDS=float(os.environ.get('ARBM_MESH_TOTAL_BUDGET_SECONDS','105'))
LOCAL_VLM_RESERVE_SECONDS=float(os.environ.get('ARBM_LOCAL_VLM_RESERVE_SECONDS','25'))
GATEWAY_TIMEOUT_CAP_SECONDS=float(os.environ.get('ARBM_GATEWAY_TIMEOUT_CAP_SECONDS','45'))
MAX_SESSION_STORES=int(os.environ.get('ARBM_MAX_SESSION_STORES','32'))
SESSION_STORES={}
CURRENT_SESSION_KEY='bootstrap'


def _fresh_state():
    return {'step':0,'previous':'','executed':0,'phase':'plan','plan':'','memory':[],
            'history':[],'facts':[],'wait_responses':0,'provider_waits':0,'cooldowns':{},
            'terminal':'','provider':'','model':'','visual_memory':'','visual_memory_meta':None,
            'gimp_specialist':{}}


def _fresh_elite():
    return EliteController(
        fast_latency_s=float(os.environ.get('ARBM_ELITE_FAST_LATENCY_S','8')),
        hard_latency_s=float(os.environ.get('ARBM_ELITE_HARD_LATENCY_S','20')),
        max_waits=int(os.environ.get('ARBM_ELITE_MAX_WAITS','2')),
        max_stall=int(os.environ.get('ARBM_ELITE_MAX_STALL','3')))


def _new_session_bundle():
    return {'state':_fresh_state(),'verifier':Verifier(),'milestones':Milestones(),
            'elite':_fresh_elite(),'health':{'last_event':'initializing','last_error':'','retry':0,'pending_since':None},
            'started':time.monotonic(),'last_used':time.time()}


def _session_key(raw=''):
    raw=str(raw or (os.environ.get('GITHUB_RUN_ID','local')+':'+os.environ.get('TASK_ID','unknown')))
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def activate_session(raw=''):
    global STATE,VERIFIER,MILESTONES,ELITE,HEALTH,STARTED,CURRENT_SESSION_KEY
    key=_session_key(raw); bundle=SESSION_STORES.get(key)
    if bundle is None:
        if len(SESSION_STORES)>=MAX_SESSION_STORES:
            oldest=min(SESSION_STORES,key=lambda k:SESSION_STORES[k]['last_used']); SESSION_STORES.pop(oldest,None)
        bundle=_new_session_bundle(); SESSION_STORES[key]=bundle
    bundle['last_used']=time.time(); CURRENT_SESSION_KEY=key
    STATE=bundle['state']; VERIFIER=bundle['verifier']; MILESTONES=bundle['milestones']; ELITE=bundle['elite']; HEALTH=bundle['health']; STARTED=bundle['started']
    return key


def mesh_remaining(started):
    return max(0.0,MESH_TOTAL_BUDGET_SECONDS-(time.monotonic()-started))


def mesh_external_budget(started,cap):
    return max(2.0,min(float(cap),max(0.0,mesh_remaining(started)-LOCAL_VLM_RESERVE_SECONDS)))


def mesh_local_budget(started,cap=80):
    return max(2.0,min(float(cap),mesh_remaining(started)))

RECOVERY = [
    'Observe foreground and choose one visible control for the next subtask.',
    'Previous action had no verified effect. Obtain fresh observation; identify the foreground window before acting.',
    'Replan with an independent strategy: keyboard navigation or bring target app forward. Do not repeat failed coordinates.',
    'Use another control or GUI path. Desktop icons may be occluded: show Desktop or use Files. Use centers and double-click to open files.',
    'Alternate FREE provider/model requested. Reassess screenshot, subtask and target. Avoid previous commands.',
    'Final contextual recovery: choose a genuinely different GUI route; never loop or claim completion.'
]

def content_parts(content):
    texts,images=[],[]
    if isinstance(content,str):return content,images
    for item in content if isinstance(content,list) else []:
        if not isinstance(item,dict):continue
        if item.get('type')=='text':texts.append(str(item.get('text') or ''))
        if item.get('type')=='image_url':
            img=item.get('image_url') or {};url=img.get('url','') if isinstance(img,dict) else ''
            if url.startswith('data:image/'):images.append(url)
    return '\n'.join(texts),images

def oidc_token():
    url=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL'];token=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']
    target=url+('&' if '?' in url else '?')+'audience=arbm-sist-benchmark'
    try:
        status,data,_=request_json(
            target,headers={'Authorization':'Bearer '+token},timeout=20)
    except (SafeHttpError,OSError,TimeoutError,ValueError) as exc:
        raise RuntimeError('OIDC_TRANSPORT_FAILED:'+type(exc).__name__) from exc
    if status != 200 or not isinstance(data,dict) or not str(data.get('value') or ''):
        raise RuntimeError('OIDC_TOKEN_UNAVAILABLE:'+str(status))
    return data['value']

def task_from(messages):
    system='\n'.join(content_parts(m.get('content'))[0] for m in messages if m.get('role')=='system')
    match=re.search(r'You are asked to complete the following task:\s*(.*)$',system,re.S)
    return match.group(1).strip() if match else system[-7000:]

def latest_observation(messages):
    users=[m for m in messages if m.get('role')=='user']
    if not users:return '', ''
    text,images=content_parts(users[-1].get('content'))
    return text,images[-1] if images else ''

def log_event(data):
    HEALTH['last_event']=data.get('status','unknown')
    if data.get('reason'):HEALTH['last_error']=data['reason']
    HEALTH['retry']=data.get('attempt',0)
    event={'timestamp':time.time(),'session_id':CURRENT_SESSION_KEY,'elapsed_seconds':round(time.monotonic()-STARTED,2),**data,'step':STATE['step'],'phase':STATE['phase'],'task_id':os.environ.get('TASK_ID'),
           'commit':os.environ.get('GITHUB_SHA'),'verifier':VERIFIER.last_result,'semantic':MILESTONES.context()}
    with open(LOG,'a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n')

def heartbeat():
    while not STOP.wait(30):
        event={'status':'HEARTBEAT','task_id':os.environ.get('TASK_ID'),'step':STATE['step'],
               'phase':STATE['phase'],'provider':STATE['provider'],'model':STATE['model'],
               'last_milestone':MILESTONES.verified[-1] if MILESTONES.verified else None,
               'elapsed_seconds':round(time.monotonic()-STARTED),'terminal':STATE['terminal'],**HEALTH}
        print(json.dumps(event),flush=True)


def terminal(reason):
    STATE['terminal']=reason
    log_event({'status':'TERMINAL_FAIL','reason':reason,'agent_build':EXPECTED_BUILD})
    return 'FAIL'

def track_attempts(data):
    for a in data.get('provider_attempts') or []:
        key=str(a.get('route'))+':'+str(a.get('model'))
        status=a.get('status')
        seconds=0
        if status==200 and a.get('route') in ('groq-multimodal-free','groq-accessibility-free'):
            seconds=max(25,min(65,float(a.get('prompt_tokens') or 4500)/7000*60+3))
        elif status==413:seconds=3600
        elif status in (401,403,404):seconds=3600
        elif status==429:
            try:seconds=max(65,min(3600,float(a.get('retry_after') or 65)))
            except (ValueError,TypeError):seconds=65
        elif isinstance(status,int) and status>=500:seconds=30
        elif a.get('contract_error'):seconds=90
        if seconds:STATE['cooldowns'][key]=int((time.time()+seconds)*1000)

def request_gateway(body, timeout=75):
    raw=json.dumps(body,ensure_ascii=False).encode()
    headers={'Authorization':'Bearer '+oidc_token(),'Content-Type':'application/json'}
    try:
        status,data,_=request_json(
            UPSTREAM,method='POST',headers=headers,data=raw,
            timeout=max(2,min(float(timeout),75)))
        return status,data if isinstance(data,dict) else {'status':'INVALID_UPSTREAM_RESPONSE'}
    except (SafeHttpError,OSError,TimeoutError,ValueError,json.JSONDecodeError) as exc:
        return 503,{'status':'TRANSPORT_ERROR','error_type':type(exc).__name__}


def _local_contract_failure(attempts):
    local=[a for a in attempts if a.get('route')=='local-cloud-vlm']
    if not local:return False
    statuses={a.get('status') for a in local}
    return bool(statuses & {'local_contract_retry','local_contract_exhausted','local_model_error'}) and not any(a.get('status')==200 for a in local)


def request_mesh(body):
    if not body.get('screenshot_data_url'): return request_gateway(body)
    started=time.monotonic()
    body={**body,'request_budget_ms':60000}
    router_attempts=[]
    def groq_router():
        result, attempts=GROQ_FREE_ROUTE.call(body,budget=mesh_external_budget(started,55))
        router_attempts.extend(attempts)
        if result:
            return 200,{'ok':True,'status':'PASS','pipeline':EXPECTED_PIPELINE,
                'agent_build':EXPECTED_BUILD,**result,'provider_attempts':router_attempts,
                'mandatory_cost_usd':0,'paid_fallback_used':False,'scoreable':False,
                'github_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID')}
        return None
    def router():
        result, attempts=FREE_ROUTE.call(body,budget=mesh_external_budget(started,55))
        router_attempts.extend(attempts)
        if result:
            return 200,{'ok':True,'status':'PASS','pipeline':EXPECTED_PIPELINE,
                'agent_build':EXPECTED_BUILD,**result,'provider_attempts':router_attempts,
                'mandatory_cost_usd':0,'paid_fallback_used':False,'scoreable':False,
                'github_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID')}
        return None
    def local_router():
        result, attempts=LOCAL_VLM_ROUTE.call(body,budget=mesh_local_budget(started,80))
        router_attempts.extend(attempts)
        if result:
            return 200,{'ok':True,'status':'PASS','pipeline':EXPECTED_PIPELINE,
                'agent_build':EXPECTED_BUILD,**result,'provider_attempts':router_attempts,
                'mandatory_cost_usd':0,'paid_fallback_used':False,'scoreable':False,
                'github_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID')}
        return None
    if os.environ.get('ARBM_VALIDATION_SPEND_MODE','zero') != 'zero':
        return 503,{'status':'NON_ZERO_SPEND_MODE_FORBIDDEN','provider_attempts':router_attempts,
                    'mandatory_cost_usd':0,'paid_fallback_used':False}
    def text_router():
        remaining=mesh_external_budget(started,45)
        raw=[{'role':'system','content':'Return exactly one JSON desktop action. Use only the provided accessibility tree and verified facts. Never claim visual details that are not in the tree.'},
             {'role':'user','content':openrouter_prompt({**body,'screenshot_data_url':''})}]
        result, attempts=FREE_ROUTE.call(body,budget=remaining,raw_messages=raw,raw_tokens=900)
        router_attempts.extend(attempts)
        if not result:return None
        try:
            text=str(result.get('text') or '').strip()
            if text.startswith('`'):text=text.split('\n',1)[1].rsplit('`',1)[0]
            action=canonical_action(json.loads(text))
        except (ValueError,TypeError,json.JSONDecodeError):
            return None
        return 200,{'ok':True,'status':'PASS','pipeline':EXPECTED_PIPELINE,'agent_build':EXPECTED_BUILD,
            'action':action,'provider':'openrouter-free-text','model':result.get('model'),
            'provider_attempts':router_attempts,'mandatory_cost_usd':0,'paid_fallback_used':False,'scoreable':False,
            'github_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID')}
    if body.get('provider_hint')=='text':
        response=text_router()
        if response:return response
    response=router()
    if response:return response
    response=groq_router()
    if response:return response
    # Preserve an independent quota-free path before the long remote gateway.
    response=local_router()
    if response:return response
    body['request_budget_ms']=max(1000,min(60000,int(mesh_external_budget(started,60)*1000)))
    http,data=request_gateway(body,timeout=mesh_external_budget(started,GATEWAY_TIMEOUT_CAP_SECONDS))
    if http==200 and isinstance(data,dict) and data.get('ok') is True:
        if router_attempts:data['provider_attempts']=(data.get('provider_attempts') or [])+router_attempts
        return http,data
    gateway_attempts=(data.get('provider_attempts') or []) if isinstance(data,dict) else []
    response=text_router()
    if response:
        response[1]['provider_attempts']=gateway_attempts+router_attempts
        return response
    all_attempts=gateway_attempts+router_attempts
    if _local_contract_failure(all_attempts):
        return 422,{'status':'LOCAL_ACTION_CONTRACT_EXHAUSTED','provider_attempts':all_attempts,
                    'mandatory_cost_usd':0,'paid_fallback_used':False}
    local_transient=any(a.get('route')=='local-cloud-vlm' and a.get('status') in ('local_model_error','budget_exceeded') for a in all_attempts)
    return 503,{'status':'LOCAL_TRANSIENT_FAILURE_CURRENT_CYCLE' if local_transient else 'FREE_MESH_EXHAUSTED_CURRENT_CYCLE',
                'provider_attempts':all_attempts,
                'mandatory_cost_usd':0,'paid_fallback_used':False}

def try_061_calibrated(body, obs, focused_obs):
    if os.environ.get('TASK_ID') != '061':
        return None
    state=STATE.setdefault('grade061',{})
    candidate=next_calibrated_action(body.get('instruction',''),body.get('active_application','unknown'),focused_obs,state)
    if not candidate:
        if state.get('hard_fail'):
            return terminal('GRADE061_'+str(state['hard_fail']))
        if state.get('owned') and not state.get('terminal_failed'):
            log_event({'status':'GRADE061_OWNERSHIP_HOLD','run_waits':state.get('run_waits',0),
                       'reference_rmse':state.get('reference_rmse')})
            return 'WAIT'
        return None
    if candidate.get('action')=='finish':
        proof=CAL_DONE.search(str(focused_obs or '')) or CAL_DONE.search(str(obs or ''))
        if proof and state.get('reference_rmse',999)<=20:
            STATE['phase']='done'
            log_event({'status':'GRADE061_VERIFIED_FINISH','proof':proof.group(0),
                       'reference_rmse':state.get('reference_rmse')})
            return 'DONE'
        log_event({'status':'GRADE061_FINISH_REJECTED','action':candidate}); return 'WAIT'
    try:
        action=ground_action(candidate,body.get('active_application','unknown'),focused_obs,body.get('verified_milestones',[]))
        decision=apply_live_policy(action,body.get('active_application','unknown'),focused_obs,body.get('verified_milestones',[]))
        senior_review=require_senior_elite(
            action,task_id=os.environ.get('TASK_ID'),source='061-calibrated',
            state=STATE,verifier=VERIFIER.last_result,
            recent_commands=[x['command'] for x in STATE['history'][-6:]])
        log_event({'status':'SENIOR_ELITE_BOARD_PASS','source':'061-calibrated',
                   'pass':senior_review['pass'],'total':senior_review['total'],
                   'lanes':senior_review['lanes']})
    except ValueError as exc:
        log_event({'status':'GRADE061_POLICY_REJECTED','reason':str(exc),'action':candidate})
        return 'WAIT' if state.get('owned') else None
    if decision.get('kind')!=DecisionKind.EXEC.value or action.get('action')!='exec':
        return 'WAIT' if state.get('owned') else None
    command=action['command']
    elite_action=ELITE.before_action(command,action.get('target'))
    if not elite_action['allow']:
        log_event({'status':'GRADE061_TABU_REJECTED','command':command,'reason':elite_action['reason']}); return 'WAIT'
    STATE['plan']=str(action.get('plan') or STATE['plan'])[:1400]
    STATE['previous']=command; STATE['executed']+=1; STATE['wait_responses']=0; STATE['provider_waits']=0
    STATE['history'].append({'command':command,'expected':action.get('expected_change',''),'source':'061-calibrated'})
    STATE['history']=STATE['history'][-12:]
    VERIFIER.issued(command)
    log_event({'status':'GRADE061_ACTION_ISSUED','command':command,'phase':action.get('specialist_phase')})
    log_event({'status':'ACTION_ISSUED','command':command,'source':'reference-pair-calibrated'})
    return '```python\n'+command+'\n```'

def _ack_gimp_pending(state, obs):
    phase=state.get('pending_phase')
    if not phase: return 'NONE'
    low=str(obs or '').casefold(); progress=bool(VERIFIER.last_result.get('progress'))
    dialog=all(x in low for x in ('get sample colors','apply','close'))
    ok=False
    if phase=='open-colorize': ok=dialog
    elif phase=='convert-profile': ok='import image from a color profile' not in low and 'gimp' in low
    elif phase in ('enable-subcolors','disable-original-intensity','disable-hold-intensity'):
        ok=dialog
    elif phase=='sample-colors': ok=dialog and (progress or 'cancel' in low)
    elif phase=='apply-colorize': ok=('cancel' in low) or (dialog and progress)
    elif phase=='close-colorize': ok=not dialog and 'gimp' in low
    elif phase in ('export-open','export-name-focus'): ok='export image' in low
    elif phase=='export-name': ok=bool(state.get('output_name')) and str(state['output_name']).casefold() in low
    elif phase=='export-submit': ok='export image as jpeg' in low
    elif phase=='export-confirm': ok='export image as jpeg' not in low and 'gimp' in low
    elif phase=='verify-output-open': ok=bool(state.get('output_name')) and str(state['output_name']).casefold() in low and 'open' in low
    elif phase=='export-baseline': ok='arbm061_export_baseline_ready' in low
    elif phase=='export-baseline-return': ok='gimp' in low and 'terminal' not in low
    elif phase=='verify-output-physical': ok=('arbm061_gimp_export_provenance_success' in low or 'arbm061_gimp_export_provenance_fail' in low)
    elif phase=='export-original-overwrite-cancel': ok='already exists' not in low
    if not ok:
        state['pending_waits']=state.get('pending_waits',0)+1
        limit=12 if phase in ('sample-colors','apply-colorize','close-colorize','export-confirm','verify-output-physical') else 4
        return 'WAIT' if state['pending_waits']<=limit else 'FAIL'
    flags={'open-colorize':'colorize_open_requested','enable-subcolors':'use_subcolors_enabled',
           'disable-original-intensity':'original_intensity_disabled','disable-hold-intensity':'hold_intensity_disabled',
           'sample-colors':'sample_colors_requested','apply-colorize':'colorize_applied','close-colorize':'colorize_closed',
           'export-open':'export_open_requested','export-name-focus':'export_name_requested','export-name':'export_name_typed',
           'export-submit':'export_submitted','export-confirm':'export_confirmed','verify-output-open':'output_verify_open',
           'export-baseline':'export_baseline_captured','export-baseline-return':'export_baseline_returned'}
    if phase in flags: state[flags[phase]]=True
    if phase=='sample-colors' and 'cancel' in low: state['sample_colors_processing']=True
    if phase=='apply-colorize' and 'cancel' in low: state['colorize_processing']=True
    if phase=='export-original-overwrite-cancel':
        for k in ('export_name_requested','export_name_typed','export_submitted','export_confirmed','output_verify_open'): state[k]=False
    state.pop('pending_phase',None); state['pending_waits']=0
    log_event({'status':'GIMP_SPECIALIST_PHASE_ACK','phase':phase,'progress':progress})
    return 'ACK'

def try_gimp_specialist(body, obs, focused_obs):
    specialist_state=STATE.setdefault('gimp_specialist',{})
    ack=_ack_gimp_pending(specialist_state,focused_obs)
    if ack=='WAIT':
        log_event({'status':'GIMP_SPECIALIST_PENDING_HOLD','phase':specialist_state.get('pending_phase')}); return 'WAIT'
    if ack=='FAIL':
        return terminal('GIMP_SPECIALIST_PHASE_UNVERIFIED')
    candidate=next_recovery_action(body.get('instruction',''),body.get('active_application','unknown'),focused_obs,specialist_state)
    if not candidate:
        if specialist_state.get('export_provenance_error'):
            log_event({'status':'GIMP_OUTPUT_PROVENANCE_UNPROVEN','reason':specialist_state.get('export_provenance_error')})
            return terminal('AGENT_OUTPUT_PROVENANCE_UNPROVEN')
        if specialist_state.get('profile_modal_error'):
            log_event({'status':'GIMP_PROFILE_CONVERT_CONTROL_UNRESOLVED','waits':specialist_state.get('profile_modal_missing_convert_waits',0)})
            return terminal('GIMP_PROFILE_CONVERT_CONTROL_UNRESOLVED')
        if specialist_state.get('colorize_processing'):
            specialist_state['uncertain_turns']=0; log_event({'status':'GIMP_SPECIALIST_COLORIZE_PROCESSING_HOLD'}); return 'WAIT'
        if specialist_state.get('owned'):
            specialist_state['uncertain_turns']=specialist_state.get('uncertain_turns',0)+1
            log_event({'status':'GIMP_SPECIALIST_OWNERSHIP_HOLD','uncertain_turns':specialist_state['uncertain_turns']}); return 'WAIT'
        return None
    try:
        action=ground_action(candidate,body.get('active_application','unknown'),focused_obs,body.get('verified_milestones',[]))
        decision=apply_live_policy(action,body.get('active_application','unknown'),focused_obs,body.get('verified_milestones',[]))
        board_verifier=VERIFIER.last_result
        if (action.get('action')=='finish'
                and specialist_state.get('output_physical_provenance') is True
                and re.fullmatch(r'[0-9a-f]{64}',str(specialist_state.get('output_provenance_sha256') or ''),re.I)
                and VERIFIER.changes > 0 and VERIFIER.no_progress < 2):
            board_verifier={**VERIFIER.last_result,'progress':True,'no_progress':0,
                            'reason':'gimp_physical_provenance_verified'}
        senior_review=require_senior_elite(
            action,task_id=os.environ.get('TASK_ID'),source='gimp-specialist',
            state=STATE,verifier=board_verifier,
            recent_commands=[x['command'] for x in STATE['history'][-6:]])
        log_event({'status':'SENIOR_ELITE_BOARD_PASS','source':'gimp-specialist',
                   'pass':senior_review['pass'],'total':senior_review['total'],
                   'lanes':senior_review['lanes']})
    except ValueError as exc:
        log_event({'status':'GIMP_SPECIALIST_POLICY_REJECTED','reason':str(exc),'action':candidate})
        if specialist_state.get('owned'):
            specialist_state['policy_holds']=specialist_state.get('policy_holds',0)+1
            log_event({'status':'GIMP_SPECIALIST_POLICY_HOLD','reason':str(exc),'policy_holds':specialist_state['policy_holds']}); return 'WAIT'
        return None
    if action.get('action')=='finish':
        specialist_complete=(specialist_state.get('colorize_closed') and specialist_state.get('export_confirmed') and specialist_state.get('output_verify_open') and specialist_state.get('output_physical_provenance') and bool(specialist_state.get('output_provenance_sha256')))
        if decision.get('kind')==DecisionKind.FINISH_CANDIDATE.value and specialist_complete and VERIFIER.can_finish(action,obs):
            STATE['phase']='done';log_event({'status':'GIMP_SPECIALIST_VERIFIED_FINISH','action':action});return 'DONE'
        log_event({'status':'GIMP_SPECIALIST_FINISH_REJECTED','action':action});return 'WAIT'
    if decision.get('kind')!=DecisionKind.EXEC.value or action.get('action')!='exec':
        if specialist_state.get('owned'):
            log_event({'status':'GIMP_SPECIALIST_DECISION_HOLD','decision':decision.get('kind')}); return 'WAIT'
        return None
    command=action['command']
    if rejects_visual_navigation_loop(action,body['instruction'],body.get('active_application','unknown'),MILESTONES.stalled):
        log_event({'status':'GIMP_SPECIALIST_LOOP_REJECTED','command':command}); return 'WAIT' if specialist_state.get('owned') else None
    recent=[x['command'] for x in STATE['history'][-6:]]
    if VERIFIER.no_progress and command in recent:
        log_event({'status':'GIMP_SPECIALIST_REPEAT_REJECTED','command':command}); return 'WAIT' if specialist_state.get('owned') else None
    elite_action=ELITE.before_action(command,action.get('target'))
    if not elite_action['allow']:
        log_event({'status':'GIMP_SPECIALIST_TABU_REJECTED','command':command,'reason':elite_action['reason']}); return 'WAIT' if specialist_state.get('owned') else None
    STATE['plan']=str(action.get('plan') or STATE['plan'])[:1400]
    STATE['previous']=command;STATE['executed']+=1;STATE['wait_responses']=0;STATE['provider_waits']=0
    STATE['history'].append({'command':command,'expected':action.get('expected_change',''),'source':'gimp-specialist'})
    STATE['history']=STATE['history'][-12:]
    specialist_state['owned']=True;specialist_state['uncertain_turns']=0
    phase=action.get('specialist_phase')
    tracked={'open-colorize','convert-profile','enable-subcolors','disable-hold-intensity','disable-original-intensity','sample-colors','apply-colorize','close-colorize','export-open','export-name-focus','export-name','export-submit','export-confirm','verify-output-open','export-baseline','export-baseline-return','verify-output-physical','export-original-overwrite-cancel'}
    if phase in tracked:
        specialist_state['pending_phase']=phase; specialist_state['pending_waits']=0
    VERIFIER.issued(command)
    if isinstance(action.get('checkpoint'),dict):MILESTONES.expect(action,obs)
    log_event({'status':'GIMP_SPECIALIST_ACTION_ISSUED','command':command,'checkpoint':action.get('checkpoint')})
    log_event({'status':'ACTION_ISSUED','command':command,'source':'gimp-style-specialist'})
    return '```python\n'+command+'\n```'
def call_mesh(messages):
    if STATE.get('step',0)==0 and not STATE.get('terminal'): ELITE.reset()
    if STATE['terminal']:return 'FAIL'
    if time.monotonic()-STARTED>=MAX_TASK_SECONDS:return terminal('TASK_DEADLINE')
    STATE['step']+=1; STATE.setdefault('facts',[])
    obs,screenshot=latest_observation(messages); focused_obs,active_application=foreground_context(obs)
    had_semantic_expectation=MILESTONES.pending is not None
    verification=VERIFIER.observe(obs,screenshot); semantic=MILESTONES.observe(obs)
    semantic_verified=semantic.get('status')=='VERIFIED'
    semantic_partial=semantic.get('status')=='PARTIAL_PROGRESS'
    semantic_progress=semantic_verified or semantic_partial
    if had_semantic_expectation and verification.get('progress') and not semantic_progress:
        VERIFIER.no_progress += 1
        VERIFIER.last_result={**VERIFIER.last_result,'progress':False,'reason':'visual_change_without_semantic_checkpoint','no_progress':VERIFIER.no_progress,'recovery_level':VERIFIER.recovery_level}; verification=VERIFIER.last_result
    elite_decision=ELITE.observe(bool(semantic_progress if had_semantic_expectation else verification.get('progress')))
    if STATE['history'] and 'outcome' not in STATE['history'][-1]:
        STATE['history'][-1]['outcome']={'progress':bool(verification.get('progress')),'semantic_verified':semantic_verified,'semantic_partial':semantic_partial,'verifier_reason':verification.get('reason'),'no_progress':verification.get('no_progress'),'milestone':semantic.get('milestone'),'partial_progress':semantic.get('progress')}
    if semantic_partial:
        log_event({'status':'SEMANTIC_PARTIAL_PROGRESS','progress':semantic.get('progress')})
    if semantic_verified:
        STATE['memory'].append('OBSERVED MILESTONE: '+json.dumps(semantic['milestone'],ensure_ascii=False)); STATE['memory']=STATE['memory'][-8:]
        ELITE.checkpoint(semantic['milestone']); log_event({'status':'MILESTONE_VERIFIED','milestone':semantic['milestone'],'backtrack_anchor':ELITE.recovery_anchor()})
        if screenshot and not STATE.get('visual_memory'): STATE['visual_memory']=screenshot; STATE['visual_memory_meta']=semantic['milestone']
    task091_state=STATE.get('task091_specialist') if isinstance(STATE.get('task091_specialist'),dict) else {}
    task091_in_progress=(_task091_match(task_from(messages))
                         and bool(task091_state.get('owned'))
                         and not task091_state.get('handoff')
                         and not task091_state.get('handoff_reason'))
    if semantic_terminal(MILESTONES.stalled, VERIFIER.no_progress) and not task091_in_progress:
        return terminal('SEMANTIC_RECOVERY_EXHAUSTED')
    if STATE['step']>MAX_STEPS:
        return terminal('STEP_BUDGET')
    if (VERIFIER.no_progress>=MAX_NO_PROGRESS or STATE['wait_responses']>=MAX_WAIT_RESPONSES) and not task091_in_progress:
        return terminal('RECOVERY_EXHAUSTED')
    STATE['phase']='plan' if (elite_decision['mode']=='replan' or VERIFIER.no_progress>=2 or not STATE['plan']) else 'execute'
    body={'instruction':task_from(messages),'observation':obs,'screenshot_data_url':screenshot,'previous_command':STATE['previous'],'executed_count':STATE['executed'],'active_application':active_application,'memory':'\n'.join([STATE['plan']]+STATE['memory'][-5:]+[str(x) for x in STATE['history'][-4:]]),'phase':STATE['phase'],'no_progress_count':VERIFIER.no_progress,'step':STATE['step'],'verifier':verification,'verified_milestones':MILESTONES.context(),'recovery_strategy':RECOVERY[VERIFIER.recovery_level],'route_cooldowns':STATE['cooldowns'],'expected_build':EXPECTED_BUILD,'performance_mode':elite_decision['mode'],'performance_reason':elite_decision['reason'],'performance_metrics':ELITE.metrics(),'reference_screenshot_data_url':STATE.get('visual_memory','') if STATE.get('visual_memory') and STATE.get('visual_memory')!=screenshot else '','reference_visual_meta':STATE.get('visual_memory_meta'),'task_ledger':{'verified_milestones':MILESTONES.context().get('verified',[]),'verified_facts':STATE.get('facts',[])[:24],'recent_outcomes':STATE['history'][-6:],'backtrack_anchor':ELITE.recovery_anchor(),'root_instruction_sha256':hashlib.sha256(task_from(messages).encode()).hexdigest(),'provider_waits':STATE.get('provider_waits',0),'cognitive_waits':STATE.get('wait_responses',0),'no_progress_count':VERIFIER.no_progress,'verifier_reason':verification.get('reason')}}
    recovery=recovery_policy(body['instruction'], body.get('active_application','unknown'), MILESTONES.stalled, VERIFIER.no_progress, VERIFIER.recovery_level, STATE['provider'], STATE.get('visual_capacity_exhausted',False))
    if recovery['strategy']:body['recovery_strategy']=recovery['strategy']
    if elite_decision['mode']=='replan' and ELITE.recovery_anchor().get('last_verified_checkpoint'):
        anchor=ELITE.recovery_anchor()['last_verified_checkpoint']; body['recovery_strategy']=(str(body.get('recovery_strategy') or '')+'\nCHECKPOINT BACKTRACK: the last independently verified state is '+json.dumps(anchor,ensure_ascii=False)+'. Treat it as known-good and do not undo verified work. From the current foreground, choose a genuinely different route toward the next unmet subgoal; the next action must name a new observable checkpoint.')[-3000:]
    if recovery['provider_hint']:body['provider_hint']=recovery['provider_hint']
    visual_recovery=visual_reference_recovery(body['instruction'],body.get('active_application','unknown'),MILESTONES.stalled)
    if visual_recovery:body['recovery_strategy']=visual_recovery
    calibrated_result=try_061_calibrated(body,obs,focused_obs)
    if calibrated_result:return calibrated_result
    task091_result=try_091_specialist(body,obs,focused_obs)
    if task091_result:return task091_result
    specialist_result=try_gimp_specialist(body,obs,focused_obs)
    if specialist_result:return specialist_result
    try:body,metrics=pack_payload(body)
    except ValueError as exc:return terminal(str(exc))
    OBS_DIR.mkdir(parents=True,exist_ok=True); evidence_path=OBS_DIR/('step_%04d.json'%STATE['step']); evidence_path.write_text(json.dumps({'request':body,'payload':metrics},ensure_ascii=False),encoding='utf-8')
    policy_rejections=0; provider_capacity_cycles=0; local_contract_cycles=0; local_transient_cycles=0
    body.setdefault('request_tabu',[])
    for attempt in range(3):
        if time.monotonic()-STARTED>=MAX_TASK_SECONDS-170:return terminal('TASK_DEADLINE')
        HEALTH['pending_since']=time.time(); metrics['after_bytes']=len(json.dumps(body,ensure_ascii=False).encode()); http,data=request_mesh(body); HEALTH['pending_since']=None
        if not isinstance(data,dict):data={'status':'INVALID_UPSTREAM_RESPONSE'}
        track_attempts(data)
        successful=[a for a in (data.get('provider_attempts') or []) if a.get('status')==200 and a.get('latency_seconds') is not None]
        if successful: ELITE.record_latency(successful[-1].get('latency_seconds'))
        log_event({'http':http,'attempt':attempt+1,'status':data.get('status'),'provider':data.get('provider'),'model':data.get('model'),'agent_build':data.get('agent_build'),'pipeline':data.get('pipeline'),'provider_attempts':data.get('provider_attempts',[]),'action':data.get('action'),'mandatory_cost_usd':data.get('mandatory_cost_usd'),'paid_fallback_used':data.get('paid_fallback_used'),'transition_review':data.get('transition_review'),'error':data.get('error'),'detail':str(data.get('detail') or '')[:200],'payload':metrics,'observation_file':str(evidence_path),'canonical_foreground_sha256':body.get('canonical_foreground_sha256')})
        if data.get('pipeline') or http==200:
            try:validate_response(data,EXPECTED_PIPELINE,EXPECTED_BUILD)
            except ValueError as exc:return terminal(str(exc))
        if http in (401,403):return terminal('ENDPOINT_AUTH_OR_VERSION')
        if data.get('status')=='LOCAL_TRANSIENT_FAILURE_CURRENT_CYCLE':
            local_transient_cycles+=1; body['provider_hint']='text' if attempt==0 else 'openrouter'; log_event({'status':'LOCAL_TRANSIENT_RETRY','attempt':attempt+1}); continue
        if data.get('status') in LOCAL_FALLBACK_CAPACITY_STATUSES | {'FREE_MESH_EXHAUSTED_CURRENT_CYCLE'}:
            provider_capacity_cycles+=1; body['provider_hint']='text' if attempt else 'openrouter'; log_event({'status':'EAGER_FREE_FAILOVER','attempt':attempt+1,'reason':data.get('status')}); continue
        if data.get('status') in LOCAL_CONTRACT_STATUSES:
            local_contract_cycles+=1
            body['memory']=(body['memory']+'\nLOCAL ACTION CONTRACT REPAIR: previous local output could not be safely compiled. Use one exact visible accessibility label or a literal keyboard action. Do not treat this as provider capacity.')[-4500:]
            body['provider_hint']='text' if attempt==0 else 'openrouter'
            log_event({'status':'LOCAL_ACTION_CONTRACT_RETRY','attempt':attempt+1,'reason':data.get('status')}); continue
        if http==409:
            if data.get('status')!='REPLAN_REQUIRED':return terminal('ENDPOINT_CONFLICT')
            reason=str(data.get('review_reason') or 'independent reviewer requested replanning'); body['memory']=(body['memory']+'\nREVIEW REPLAN REQUIRED: '+reason+'. Do not repeat the rejected action; produce a new grounded action from the current observation.')[-4500:]; continue
        if http==200 and data.get('ok') is True:
            try:
                allow_canonical=(str(data.get('provider') or '')=='local-cloud-vlm')
                recent_commands=[x['command'] for x in STATE['history'][-6:]]
                action=ground_action(
                    data.get('action'),body.get('active_application','unknown'),focused_obs,
                    body.get('verified_milestones',[]),allow_canonical=allow_canonical,
                    verifier_result=VERIFIER.last_result,recent_commands=recent_commands)
                decision=apply_live_policy(action,body.get('active_application','unknown'),focused_obs,body.get('verified_milestones',[]))
                senior_review=require_senior_elite(
                    action,task_id=os.environ.get('TASK_ID'),source='generic-mesh',
                    state=STATE,verifier=VERIFIER.last_result,recent_commands=recent_commands)
                log_event({'status':'SENIOR_ELITE_BOARD_PASS','source':'generic-mesh',
                           'pass':senior_review['pass'],'total':senior_review['total'],
                           'lanes':senior_review['lanes']})
            except ValueError as exc:
                policy_rejections+=1
                rejected_action=data.get('action') if isinstance(data.get('action'),dict) else {}
                body['request_tabu'].append({
                    'action':rejected_action.get('action') or 'exec',
                    'command':str(rejected_action.get('command') or ''),
                    'target':rejected_action.get('target') if isinstance(rejected_action.get('target'),dict) else {},
                    'weight':2,
                    'reason':str(exc)[:120],
                    'attempt':attempt+1,
                })
                body['request_tabu']=body['request_tabu'][-12:]
                body['memory']=(body['memory']+'\nPOLICY REJECTED: '+str(exc)+'. Replan within deterministic v32 state constraints. This is a local action-contract rejection, not provider-capacity evidence.')[-4500:]
                body['provider_hint']='openrouter' if str(data.get('provider') or '').startswith('groq') else 'text'
                log_event({'status':'LOCAL_POLICY_REJECTED','reason':str(exc),'attempt':attempt+1,'request_tabu':body['request_tabu'][-4:]})
                continue
            decision_kind=decision['kind']
            if decision_kind==DecisionKind.NOOP_VERIFIED.value:
                log_event({'status':'NOOP_VERIFIED','checkpoint':action.get('checkpoint')}); STATE['wait_responses']+=1; ELITE.note_wait(); return 'WAIT'
            if decision_kind==DecisionKind.HOLD_CAPACITY.value:
                STATE['provider_waits']=STATE.get('provider_waits',0)+1; log_event({'status':'HOLD_CAPACITY','provider_waits':STATE['provider_waits']}); return 'WAIT'
            for fact in verified_facts(action,focused_obs):
                entry='OBSERVED SOURCE: '+json.dumps(fact,ensure_ascii=False)
                if entry not in STATE['memory']:STATE['memory'].append(entry)
                if fact not in STATE['facts']: STATE['facts'].append(fact)
            STATE['facts']=STATE['facts'][-24:]; STATE['memory']=STATE['memory'][-12:]
            kind=action['action']; STATE['provider'],STATE['model']=data.get('provider',''),data.get('model',''); STATE['plan']=str(action.get('plan') or STATE['plan'])[:1400]
            if kind=='finish':
                if MILESTONES.verified and MILESTONES.stalled==0 and VERIFIER.can_finish(action,obs): STATE['phase']='done';log_event({'status':'VERIFIED_FINISH','action':action});return 'DONE'
                body['memory']=(body['memory']+'\nFINISH REJECTED: no sufficient observed completion. Verify all outputs on screen.')[-4500:]; continue
            if kind=='exec':
                command=action['command']
                if rejects_visual_navigation_loop(action, body['instruction'], body.get('active_application','unknown'), MILESTONES.stalled):
                    body['memory']=(body['memory']+'\nVISUAL_NAVIGATION_LOOP_REJECTED: Ctrl+O was already used without a verified visual milestone. Use the visible dialog deliberately or make a target-image edit instead. Do not repeat it.')[-4500:]; body.pop('provider_hint',None); log_event({'status':'VISUAL_NAVIGATION_LOOP_REJECTED','command':command}); continue
                recent=recent_commands
                bounded_wps_escape=allow_bounded_wps_escape_repeat(
                    action,body.get('active_application','unknown'),VERIFIER.last_result,recent)
                bounded_wps_modal_close=allow_bounded_wps_modal_close_repeat(
                    action,body.get('active_application','unknown'),VERIFIER.last_result,recent)
                if VERIFIER.no_progress and command in recent and bounded_wps_escape:
                    log_event({'status':'BOUNDED_WPS_ESCAPE_REPEAT_ALLOWED','command':command,'attempt':attempt+1,
                               'verifier_reason':VERIFIER.last_result.get('reason')})
                if VERIFIER.no_progress and command in recent and bounded_wps_modal_close:
                    log_event({'status':'BOUNDED_WPS_MODAL_CLOSE_REPEAT_ALLOWED','command':command,'attempt':attempt+1,
                               'verifier_reason':VERIFIER.last_result.get('reason')})
                if VERIFIER.no_progress and command in recent and not (bounded_wps_escape or bounded_wps_modal_close):
                    body['request_tabu'].append({'action':'exec','command':command,'target':action.get('target') if isinstance(action.get('target'),dict) else {},'weight':3,'reason':'repeated-no-progress','attempt':attempt+1})
                    body['request_tabu']=body['request_tabu'][-12:]
                    body['memory']=(body['memory']+'\nNO EFFECT: rejected repeated action '+command+'. Change GUI strategy or target.')[-4500:]
                    body['provider_hint']='openrouter' if str(data.get('provider') or '').startswith('groq') else 'text'
                    route='groq-multimodal-free' if str(data.get('provider') or '').startswith('groq') else 'openrouter-multimodal-free'
                    STATE['cooldowns'][route+':'+str(data.get('model'))]=int((time.time()+90)*1000)
                    log_event({'status':'INTRA_REQUEST_TABU','reason':'repeated-no-progress','command':command,'attempt':attempt+1})
                    continue
                retry_proof=None
                if bounded_wps_escape:
                    retry_proof={
                        'fresh_observation': True,
                        'state_changed': bool(VERIFIER.last_result.get('tree_changed') or VERIFIER.last_result.get('visual_changed')),
                        'bounded_retry': True,
                        'reason': 'stacked WPS modal dismissal after independently observed foreground change',
                    }
                elif bounded_wps_modal_close:
                    retry_proof={
                        'fresh_observation': True,
                        'state_changed': False,
                        'bounded_retry': True,
                        'reason': 'one bounded retry of the explicitly observed WPS modal close control after a focus-only click',
                    }
                elite_action=ELITE.before_action(command,action.get('target'),retry_proof=retry_proof)
                if not elite_action['allow']:
                    body['request_tabu'].append({'action':'exec','command':command,'target':action.get('target') if isinstance(action.get('target'),dict) else {},'weight':3,'reason':'elite-tabu','attempt':attempt+1})
                    body['request_tabu']=body['request_tabu'][-12:]
                    body['memory']=(body['memory']+'\nELITE TABU: action rejected because it previously produced no verified progress. Replan from the current screenshot with a genuinely different control/path.')[-4500:]
                    log_event({'status':'ELITE_TABU_REJECTED','command':command,'reason':elite_action['reason'],'request_tabu':body['request_tabu'][-4:]})
                    continue
                STATE['previous']=command;STATE['executed']+=1;STATE['wait_responses']=0;STATE['provider_waits']=0; STATE['history'].append({'command':command,'expected':action.get('expected_change','')}); STATE['history']=STATE['history'][-12:]; VERIFIER.issued(command); MILESTONES.expect(action,obs); log_event({'status':'ACTION_ISSUED','command':command}); return '```python\n'+command+'\n```'
            break
        if http==413: body['observation']=body['observation'][:4000];body['memory']=body['memory'][-1500:]
        elif http==422: body['memory']=(body['memory']+'\nRecover invalid action: exec/finish/wait only. Command must be a valid literal Python string.')[-4500:]
        elif http in (429,500,502,503,504): body['route_cooldowns']=STATE['cooldowns']; time.sleep(2+attempt)
        else:break
    if local_contract_cycles or policy_rejections:
        return terminal('ACTION_CONTRACT_EXHAUSTED')
    if VERIFIER.no_progress>0 and provider_capacity_cycles==0 and local_transient_cycles==0:
        log_event({'status':'NO_PROGRESS_EXHAUSTED','no_progress':VERIFIER.no_progress,
                   'verifier_reason':VERIFIER.last_result.get('reason'),
                   'local_contract_cycles':local_contract_cycles,
                   'provider_capacity_cycles':provider_capacity_cycles})
        return terminal('NO_PROGRESS_TIMEOUT')
    if local_transient_cycles and provider_capacity_cycles==0:
        return terminal('LOCAL_FALLBACK_TRANSIENT_EXHAUSTED')
    STATE['provider_waits']=STATE.get('provider_waits',0)+1
    log_event({'status':'FREE_MESH_EXHAUSTED','provider_waits':STATE['provider_waits'],'policy_rejections':policy_rejections,'local_contract_cycles':local_contract_cycles,'provider_capacity_cycles':provider_capacity_cycles,'no_progress':VERIFIER.no_progress,'verifier_reason':VERIFIER.last_result.get('reason')})
    return terminal('PROVIDER_CAPACITY_EXHAUSTED')

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def send_json(self,code,value):
        raw=json.dumps(value).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        self.send_json(200,{'status':'ok','pipeline':EXPECTED_PIPELINE,'build':EXPECTED_BUILD}) if self.path=='/health' else self.send_json(404,{})
    def do_POST(self):
        if self.path!='/v1/chat/completions':return self.send_json(404,{'error':{'code':'not_found','message':'Not found'}})
        self.close_connection=True; self.connection.settimeout(60)
        session_raw=self.headers.get('X-ARBM-Session-ID') or (os.environ.get('GITHUB_RUN_ID','local')+':'+os.environ.get('TASK_ID','unknown'))
        with LOCK:
            activate_session(session_raw)
            try:
                messages,ingress=project_messages(self.rfile,int(self.headers.get('Content-Length','0'))); log_event({'status':'INGRESS_PROJECTED','ingress':ingress}); content=call_mesh(messages)
            except (ValueError,TimeoutError) as exc: content=terminal('INPUT_REJECTED:'+str(exc)[:120])
            except Exception as exc:
                log_event({'status':'SHIM_ERROR','error_type':type(exc).__name__,'reason':str(exc)[:200]}); content=terminal('SHIM_INTERNAL_ERROR:'+type(exc).__name__)
        return self.send_json(200,{'id':'arbm-osworld-v32-isolated','object':'chat.completion','created':int(time.time()),'model':'gpt-arbm-osworld-v32-isolated','choices':[{'index':0,'message':{'role':'assistant','content':content},'finish_reason':'stop'}],'usage':{'prompt_tokens':0,'completion_tokens':0,'total_tokens':0}})

def isolated_self_test(run_id,task,verify_budget=False,enforce_session_isolation=False):
    result={'status':'PASS','run_id':str(run_id),'task':str(task),'zero_spend':os.environ.get('ZERO_SPEND_MODE')=='HARD'}
    if not result['zero_spend']: raise SystemExit('ZERO_SPEND_MODE_HARD_REQUIRED')
    if verify_budget:
        now=time.monotonic(); aged=now-(MESH_TOTAL_BUDGET_SECONDS-LOCAL_VLM_RESERVE_SECONDS-10)
        ef=mesh_external_budget(now,55); lf=mesh_local_budget(now,80); ea=mesh_external_budget(aged,55); la=mesh_local_budget(aged,80)
        if ef>MESH_TOTAL_BUDGET_SECONDS-LOCAL_VLM_RESERVE_SECONDS+0.01: raise SystemExit('EXTERNAL_BUDGET_CONSUMES_LOCAL_RESERVE')
        if la<=ea: raise SystemExit('LOCAL_RESERVE_NOT_PRESERVED')
        result['budget']={'total_seconds':MESH_TOTAL_BUDGET_SECONDS,'local_reserve_seconds':LOCAL_VLM_RESERVE_SECONDS,'external_fresh':round(ef,3),'local_fresh':round(lf,3),'external_aged':round(ea,3),'local_aged':round(la,3)}
    if enforce_session_isolation:
        a=f'{run_id}:{task}:a'; b=f'{run_id}:{task}:b'; ka=activate_session(a); STATE['step']=17; STATE['memory'].append('a-proof'); kb=activate_session(b)
        if STATE['step']!=0 or STATE['memory']: raise SystemExit('SESSION_B_INHERITED_A')
        STATE['step']=91; STATE['memory'].append('b-proof'); activate_session(a)
        if STATE['step']!=17 or STATE['memory']!=['a-proof']: raise SystemExit('SESSION_A_NOT_RESTORED')
        activate_session(b)
        if STATE['step']!=91 or STATE['memory']!=['b-proof']: raise SystemExit('SESSION_B_NOT_RESTORED')
        result['session_isolation']={'isolated':True,'session_a':ka,'session_b':kb}
    result['transient_failure_mapping']='LOCAL_FALLBACK_TRANSIENT_EXHAUSTED'; print(json.dumps(result,sort_keys=True)); return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=True); parser.add_argument('--test-isolated-run',action='store_true'); parser.add_argument('--run-id',default=os.environ.get('GITHUB_RUN_ID','local')); parser.add_argument('--task',default=os.environ.get('TASK_ID','unknown')); parser.add_argument('--verify-budget',action='store_true'); parser.add_argument('--enforce-session-isolation',action='store_true'); args=parser.parse_args()
    if args.test_isolated_run: raise SystemExit(isolated_self_test(args.run_id,args.task,args.verify_budget,args.enforce_session_isolation))
    threading.Thread(target=heartbeat,daemon=True).start()
    if os.environ.get('ZERO_SPEND_MODE')=='HARD' and os.environ.get('ARBM_ENABLE_LOCAL_VLM')=='1': threading.Thread(target=warm_runtime,daemon=True,name='arbm-local-vlm-warmup').start()
    ThreadingHTTPServer(('127.0.0.1',8088),Handler).serve_forever()
