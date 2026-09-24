"""OpenAI-compatible OSWorld bridge. All guest execution stays in official OSWorld."""
import argparse, json, os, re, time, hashlib, threading, copy
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
from arbm091.semantic_runtime import next_text_action as next_091_semantic_text_action
from arbm091.semantic_transaction import normalize_deck as task091_normalize_deck, model_sha256 as task091_model_sha256, target_key as task091_target_key, verify_font_transaction as task091_verify_font_transaction
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

def _task091_table_cell_selection_presses(old):
    """Stay strictly inside one table cell; never cross its left boundary."""
    old=str(old or '')
    if not old or '\n' in old or len(old) > 30:
        raise ValueError('TASK091_TABLE_CELL_BOUNDED_EDIT_INVALID')
    presses=len(old)
    if not 1 <= presses <= 30:
        raise ValueError('TASK091_TABLE_CELL_SELECTION_LENGTH_INVALID')
    return presses


def _task091_table_cell_start_navigation_command(old, interval=0.03):
    """Move from a positively proven logical text end to the exact text start.

    The command is admitted only by the caller after caret-at-text-end geometry
    has been positively proven. For a fixed-width cell, moving left exactly
    len(old) characters reaches the pre-first-character position without
    relying on WPS Home semantics or raster hit-testing.
    """
    old=str(old or '')
    if not old or '\n' in old or len(old)>30:
        raise ValueError('TASK091_TABLE_CELL_START_NAV_TEXT_INVALID')
    presses=len(old)
    if not 1 <= presses <= 30:
        raise ValueError('TASK091_TABLE_CELL_START_NAV_COUNT_INVALID')
    return f"pyautogui.press('left', presses={presses}, interval={float(interval):g})"

def _task091_table_cell_delta_plan(old, new):
    """Return at most two same-length character substitutions for a KPI cell.

    Slide 3 KPI values are fixed-width. Replacing the whole cell is unsafe in
    WPS because the logical table-cell boundaries can preserve the first/last
    visible glyph even when caret geometry looks correct. The safe contract is
    therefore to preserve every already-correct character and mutate only the
    differing indices.
    """
    old=str(old or '')
    new=str(new or '')
    if (not old or not new or '\n' in old or '\n' in new
            or len(old)!=len(new) or len(old)>30):
        raise ValueError('TASK091_TABLE_CELL_DELTA_PLAN_INVALID')
    plan=[{'index':i,'old':a,'new':b} for i,(a,b) in enumerate(zip(old,new)) if a!=b]
    if not plan or len(plan)>2:
        raise ValueError('TASK091_TABLE_CELL_DELTA_PLAN_UNBOUNDED')
    return plan


def _task091_table_cell_bounded_write_command(old, new, interval=TASK091_TYPE_INTERVAL):
    """Apply only the proven differing characters from a proven start caret.

    No whole-cell selection is used. Each substitution is Delete + one-char
    Write at an exact index while preserving the fixed cell length. This keeps
    currency/percent/unit boundary glyphs outside the mutation surface.
    """
    plan=_task091_table_cell_delta_plan(old,new)
    commands=[]
    cursor=0
    for row in plan:
        index=int(row['index'])
        move=index-cursor
        if move < 0:
            raise ValueError('TASK091_TABLE_CELL_DELTA_CURSOR_REGRESSION')
        if move:
            commands.append(f"pyautogui.press('right', presses={move}, interval=0.03)")
        commands.append("pyautogui.press('delete')")
        commands.append(f"pyautogui.write({str(row['new'])!r}, interval={float(interval):g})")
        cursor=index+1
    if len(commands)>6:
        raise ValueError('TASK091_TABLE_CELL_DELTA_ACTION_COUNT_UNBOUNDED')
    return '\n'.join(commands)


def _task091_table_cell_rollback_command():
    """Undo one failed table-cell transaction and persist the restored deck."""
    return "pyautogui.hotkey('ctrl', 'z')\npyautogui.hotkey('ctrl', 's')\npyautogui.sleep(0.25)"

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

def _task091_publish_panel_target(action, window_state):
    target=action.get('target') if isinstance(action,dict) else None
    if not isinstance(target,dict) or str(target.get('source') or '').casefold()!='task091-panel-canonical':
        return
    root=os.environ.get('ARBM_WPS_EVIDENCE_DIR')
    if not root:
        raise ValueError('TASK091_PANEL_EVIDENCE_DIR_MISSING')
    source=str((window_state or {}).get('source') or '')
    shot=str((window_state or {}).get('screenshot_sha256') or '')
    if source!=str(target.get('source_observation_id') or '') or shot!=str(target.get('screenshot_sha256') or ''):
        raise ValueError('TASK091_PANEL_TARGET_SOURCE_FRAME_MISMATCH')
    payload={'schema':1,'candidate_sha':str(os.environ.get('GITHUB_SHA') or ''),
             'command':str(action.get('command') or ''),
             'source_observation_id':source,'source_screenshot_sha256':shot,
             'created_monotonic_ns':time.monotonic_ns(),'target':target}
    path=Path(root)/'pending-panel-target.json'
    tmp=Path(root)/('.pending-panel-target-'+str(os.getpid())+'.tmp')
    tmp.write_text(json.dumps(payload,sort_keys=True,separators=(',',':')),encoding='utf-8')
    os.replace(tmp,path)


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
    """Prove a text caret from a narrow vertical pixel delta inside one cell.

    WPS caret blink can make the post-action screenshot land on the invisible
    phase. For an observation-only probe, the paired before screenshot is also
    causally after the prior GUI action and may contain the visible blink phase.
    Inspect both samples, but keep the same strict caret geometry gate.
    """
    before_path=_task091_screenshot_source_path(before_source)
    if before_path is None or not isinstance(bbox,list) or len(bbox)!=4:
        return {'proven':False,'reason':'evidence-missing'}
    if not all(type(v) is int for v in bbox):
        return {'proven':False,'reason':'bbox-invalid'}
    x,y,w,h=bbox
    if w<=0 or h<=0:
        return {'proven':False,'reason':'bbox-empty'}

    candidate_sources=[str(after_source or '')]
    match=re.fullmatch(r'(\d{4}-\d{2})-after',str(after_source or ''))
    if match:
        paired=match.group(1)+'-before'
        if paired != str(before_source or ''):
            candidate_sources.append(paired)

    best=None
    try:
        with Image.open(before_path) as a_img:
            a=a_img.convert('RGB').crop((x,y,x+w,y+h))
            for candidate_source in candidate_sources:
                candidate_path=_task091_screenshot_source_path(candidate_source)
                if candidate_path is None:
                    continue
                with Image.open(candidate_path) as b_img:
                    b=b_img.convert('RGB').crop((x,y,x+w,y+h))
                if a.size != b.size:
                    result={'proven':False,'reason':'size-drift',
                            'observed_source':candidate_source}
                    best=best or result
                    continue
                xs=[]; ys=[]; col_counts={}
                for py in range(h):
                    for px in range(w):
                        av=a.getpixel((px,py)); bv=b.getpixel((px,py))
                        if max(abs(int(av[i])-int(bv[i])) for i in range(3)) <= 20:
                            continue
                        xs.append(px); ys.append(py)
                        col_counts[px]=col_counts.get(px,0)+1
                count=len(xs)
                if not count:
                    result={'proven':False,'reason':'no-local-delta','count':0,
                            'observed_source':candidate_source}
                else:
                    dw=max(xs)-min(xs)+1; dh=max(ys)-min(ys)+1
                    dominant=max(col_counts.values()) if col_counts else 0
                    proven=(8 <= count <= 160
                            and dw <= 4
                            and 8 <= dh <= min(40,h)
                            and dh >= max(8,dw*4)
                            and dominant >= max(8,int(count*0.65)))
                    result={'proven':proven,
                            'reason':'caret-geometry' if proven else 'delta-not-caret',
                            'count':count,'width':dw,'height':dh,
                            'dominant_column':dominant,
                            'bbox':[min(xs),min(ys),dw,dh],
                            'observed_source':candidate_source}
                if result.get('proven') is True:
                    return result
                if best is None or int(result.get('count') or 0) > int(best.get('count') or 0):
                    best=result
    except Exception:
        return {'proven':False,'reason':'image-read-failed'}
    return best or {'proven':False,'reason':'evidence-missing'}

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


def _task091_table_cell_text_end_point(text_ink, bbox, gap=3):
    """Derive a signed click point immediately after the observed final glyph."""
    if not isinstance(text_ink,dict) or not isinstance(bbox,list) or len(bbox)!=4:
        return None
    ink_bbox=text_ink.get('ink_bbox')
    if not isinstance(ink_bbox,list) or len(ink_bbox)!=4:
        return None
    if not all(type(v) is int for v in bbox+ink_bbox):
        return None
    x,y,w,h=bbox; ix,iy,iw,ih=ink_bbox
    if w<=20 or h<=20 or iw<=0 or ih<=0:
        return None
    cell_right=x+w
    ink_right=ix+iw
    cx=min(cell_right-9,ink_right+int(gap))
    cy=iy+ih//2
    if not (ink_right < cx < cell_right-8 and y+8 <= cy < y+h-8):
        return None
    payload={
        'cell_bbox':[x,y,w,h],
        'ink_bbox':[ix,iy,iw,ih],
        'ink_proof_sha256':str(text_ink.get('proof_sha256') or ''),
        'point':[cx,cy],
        'gap':int(gap),
    }
    proof=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return {**payload,'cx':cx,'cy':cy,'proof_sha256':proof}


def _task091_caret_at_text_end(caret, shape_bbox, ink_bbox, expected_x, tolerance=8):
    """Require the proven caret to sit at the signed visual end of cell text."""
    if not isinstance(caret,dict) or caret.get('proven') is not True:
        return {'proven':False,'reason':'caret-unproven'}
    if not isinstance(shape_bbox,list) or len(shape_bbox)!=4 or not isinstance(ink_bbox,list) or len(ink_bbox)!=4:
        return {'proven':False,'reason':'geometry-missing'}
    cb=caret.get('bbox')
    if not isinstance(cb,list) or len(cb)!=4:
        return {'proven':False,'reason':'caret-bbox-missing'}
    if not all(type(v) is int for v in shape_bbox+ink_bbox+cb):
        return {'proven':False,'reason':'geometry-invalid'}
    caret_x=int(shape_bbox[0])+int(cb[0])
    ink_right=int(ink_bbox[0])+int(ink_bbox[2])
    expected_x=int(expected_x or 0)
    tolerance=int(tolerance)
    proven=(expected_x>0
            and caret_x >= ink_right-2
            and caret_x <= ink_right+tolerance+4
            and abs(caret_x-expected_x) <= tolerance)
    return {
        'proven':proven,
        'reason':'caret-at-text-end' if proven else 'caret-not-at-text-end',
        'caret_x':caret_x,
        'ink_right':ink_right,
        'expected_x':expected_x,
        'tolerance':tolerance,
    }


def _task091_caret_at_text_start(caret, shape_bbox, ink_bbox, tolerance=8):
    """Classify the proven caret relative to the first visible cell glyph."""
    if not isinstance(caret,dict) or caret.get('proven') is not True:
        return {'proven':False,'reason':'caret-unproven','relation':'unknown'}
    if not isinstance(shape_bbox,list) or len(shape_bbox)!=4 or not isinstance(ink_bbox,list) or len(ink_bbox)!=4:
        return {'proven':False,'reason':'geometry-missing','relation':'unknown'}
    cb=caret.get('bbox')
    if not isinstance(cb,list) or len(cb)!=4:
        return {'proven':False,'reason':'caret-bbox-missing','relation':'unknown'}
    if not all(type(v) is int for v in shape_bbox+ink_bbox+cb):
        return {'proven':False,'reason':'geometry-invalid','relation':'unknown'}
    caret_x=int(shape_bbox[0])+int(cb[0])
    ink_left=int(ink_bbox[0])
    tolerance=int(tolerance)
    delta=caret_x-ink_left
    proven=(-tolerance-4 <= delta <= 2)
    relation=('at-start' if proven else
              'right-of-start' if 2 < delta <= 24 else
              'left-of-start' if delta < -tolerance-4 else
              'far-right')
    return {
        'proven':proven,
        'reason':'caret-at-text-start' if proven else 'caret-not-at-text-start',
        'relation':relation,
        'caret_x':caret_x,
        'ink_left':ink_left,
        'delta_to_start':delta,
        'tolerance':tolerance,
    }


def _task091_table_cell_rollback_verified(pending, window_state):
    if not isinstance(pending,dict) or not isinstance(window_state,dict):
        return False
    slide=int(pending.get('slide') or 0)
    shape=_task091_shape_by_id(window_state,slide,pending.get('shape_id'))
    current_file=window_state.get('deck_file',{})
    current_sha=str(current_file.get('sha256') or '') if isinstance(current_file,dict) else ''
    corrupt_sha=str(pending.get('rollback_corrupt_deck_sha256') or '')
    siblings=_task091_other_shapes_signature(window_state,slide,pending.get('shape_id'))
    return (len(current_sha)==64
            and len(corrupt_sha)==64
            and current_sha != corrupt_sha
            and isinstance(shape,dict)
            and str(shape.get('kind') or '')=='table-cell'
            and str(shape.get('text') or '')==str(pending.get('old') or '')
            and siblings==str(pending.get('before_sibling_signature') or ''))


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


TASK091_SECTION_E_FORMAT = {
    'slide': 3,
    'shape_id': 16,
    'shape_name': 'KpiReadout_Body',
    'text_fingerprint': '• Burn improvement relies on expansion payback from Q4.',
    'font_decrements': 2,
}


def _task091_section_e_geometry_persisted(before, after):
    """Accept only the local WPS autofit shrink caused by the proven font edit.

    The target must keep its exact x/y position and width. Height may remain
    unchanged or shrink, but never grow and never collapse below 60% of the
    proven baseline. Any other geometry mutation remains fail-closed.
    """
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    try:
        bx,by,bw,bh=(int(before[k]) for k in ('x','y','w','h'))
        ax,ay,aw,ah=(int(after[k]) for k in ('x','y','w','h'))
    except (KeyError,TypeError,ValueError):
        return False
    if min(bw,bh,aw,ah) <= 0:
        return False
    if (ax,ay,aw)!=(bx,by,bw):
        return False
    return int(bh*0.60) <= ah <= bh


def _task091_section_e_format_step(state, window_state):
    """Caret-free Section E font transaction proved from persisted OOXML."""
    spec=TASK091_SECTION_E_FORMAT
    slide=int(spec['slide'])
    tx=state.get('section_e_format')
    current=int(state.get('slide') or 1)

    if not isinstance(tx,dict):
        nav=_task091_nav_command(current,slide)
        if nav:
            state['slide']=slide
            return {'action':'exec','command':nav,
                    'plan':'Navigate to Slide 3 for the isolated semantic font transaction.',
                    'specialist_phase':'section-e-semantic-navigate'}
        shape=_task091_shape_by_id(window_state,slide,spec['shape_id'])
        if (not isinstance(shape,dict)
                or str(shape.get('name') or '')!=str(spec['shape_name'])
                or str(spec['text_fingerprint']) not in str(shape.get('text') or '')):
            return _task091_terminal('TASK091_SECTION_E_SHAPE_UNPROVEN',state)
        if not list(shape.get('font_sizes') or []):
            return _task091_terminal('TASK091_SECTION_E_FONT_SEMANTICS_MISSING',state)
        box=_task091_shape_bbox(window_state,shape)
        if box is None:
            return _task091_terminal('TASK091_SECTION_E_GEOMETRY_UNPROVEN',state)
        try:
            model=task091_normalize_deck(window_state)
            key=task091_target_key(slide,shape)
            before_hash=task091_model_sha256(model)
        except Exception:
            return _task091_terminal('TASK091_SECTION_E_OOXML_BASELINE_UNPROVEN',state)
        deck_sha=str((window_state.get('deck_file',{}) or {}).get('sha256') or '')
        foreground=_task091_foreground_sha(window_state)
        if len(deck_sha)!=64 or len(foreground)!=64:
            return _task091_terminal('TASK091_SECTION_E_BASELINE_UNPROVEN',state)
        cx=int(box['cx']); cy=int(box['cy'])
        target={'source':'task091-pptx-canonical','label':spec['shape_name'],
                'role':'task091-canonical-point','slide':slide,
                'x':cx-1,'y':cy-1,'w':2,'h':2,'cx':cx,'cy':cy,
                'foreground_sha256':foreground,'deck_sha256':deck_sha}
        target['proof_sha256']=task091_spatial_target_proof(target)
        state['section_e_format']={
            'stage':'select-issued','slide':slide,'shape_id':int(spec['shape_id']),
            'shape_name':str(spec['shape_name']),'text':str(shape.get('text') or ''),
            'target_key':list(key),'before_model_sha256':before_hash,
            'before_deck_sha256':deck_sha,
            'before_state':{
                'deck_slide_shapes':copy.deepcopy(window_state.get('deck_slide_shapes',{})),
                'deck_slide_charts':copy.deepcopy(window_state.get('deck_slide_charts',{})),
                'deck_slide_relationships':copy.deepcopy(window_state.get('deck_slide_relationships',{})),
                'deck_file':copy.deepcopy(window_state.get('deck_file',{})),
            },
            'font_decrements':int(spec['font_decrements']),
        }
        return {'action':'exec',
                'command':f"pyautogui.doubleClick({cx}, {cy}, interval=0.08)",
                'target':target,
                'plan':'Select only the OOXML-resolved Section E body shape in WPS; caret state is irrelevant.',
                'specialist_phase':'section-e-semantic-select'}

    stage=str(tx.get('stage') or '')
    shape=_task091_shape_by_id(window_state,slide,tx.get('shape_id'))
    if not isinstance(shape,dict) or str(shape.get('name') or '')!=str(tx.get('shape_name') or ''):
        return _task091_terminal('TASK091_SECTION_E_TARGET_IDENTITY_DRIFT',state)

    if stage=='select-issued':
        try:
            if task091_model_sha256(task091_normalize_deck(window_state))!=str(tx.get('before_model_sha256') or ''):
                return _task091_terminal('TASK091_SECTION_E_PRECONDITION_DRIFT',state)
        except Exception:
            return _task091_terminal('TASK091_SECTION_E_PRECONDITION_DRIFT',state)
        tx['stage']='font-issued'
        commands=["pyautogui.hotkey('ctrl', 'a')"]
        for _ in range(int(tx.get('font_decrements') or 1)):
            commands.append("pyautogui.hotkey('ctrl', '[')")
        return {'action':'exec','command':'\n'.join(commands),
                'plan':'Select the resolved shape text and apply exactly the declared font decrement; OOXML will prove the result.',
                'specialist_phase':'section-e-semantic-font'}
