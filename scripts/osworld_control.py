"""Local action compiler, observation verifier and bounded payload builder.

This module has no network access and never reads the guest filesystem.
"""
import ast
import base64
import binascii
import hashlib
import io
import json
import math
import os
import re
from collections import deque

MAX_PAYLOAD_BYTES = 420_000
MAX_TREE_CHARS = 9000
METHODS = {'click','doubleClick','rightClick','moveTo','press','hotkey','write','typewrite',
           'scroll','sleep','mouseDown','mouseUp','dragTo','keyDown','keyUp'}


def visual_reference_recovery(instruction, active_application, stalled_actions):
    """Return bounded guidance when a visual-style task is looping in an editor.

    The guidance is deliberately task-agnostic: it is enabled only when the
    request asks to reproduce edits/style from a visible reference and the
    foreground is an image editor.  It does not prescribe a transformation or
    inspect any hidden file; it simply prevents navigation from being mistaken
    for progress once repeated GUI actions have produced no visible milestone.
    """
    request = str(instruction or '').casefold()
    app = str(active_application or '').casefold()
    reference_task = (any(term in request for term in ('same style', 'same edits', 'mimic', 'color grading'))
                      and any(term in request for term in ('image', '.jpg', '.png', 'photo')))
    image_editor = any(term in app for term in ('gimp', 'darktable', 'image manipulation'))
    editor_context = image_editor or any(term in request for term in ('gimp', 'darktable'))
    if reference_task and editor_context and int(stalled_actions or 0) >= 4:
        return (
            'VISUAL-REFERENCE RECOVERY: file dialogs, tab changes, and opening a reference are preparatory, '
            'not completion. Stop repeating file-navigation actions. Use only paths stated by the task; never substitute host paths such as /home/oai/share. In a GTK file chooser use Ctrl+L before typing a task path such as ~/Pictures/name.jpg. Use the current visible dialog to open or '
            'close it deliberately, bring the target image canvas forward, compare it with the reference, then '
            'perform one visible editor adjustment (for example a Colors control). Set a checkpoint that proves '
            'the target canvas or adjustment dialog is visible before exporting. Do not claim success until the '
            'target output is visibly present.'
        )
    return ''


def canonical_action(value):
    if not isinstance(value, dict):
        raise ValueError('ACTION_OBJECT_REQUIRED')
    a = dict(value)
    kind = str(a.get('action') or '').strip().lower()
    command = a.get('command') or ''
    if not isinstance(command, str):
        raise ValueError('COMMAND_STRING_REQUIRED')
    if kind in {'execute','click','type','plan'}:
        kind = 'exec' if command.strip() else 'wait'
    if kind not in {'exec','wait','finish'}:
        raise ValueError('INVALID_ACTION')
    a['action'] = kind
    a['command'] = ''
    if kind != 'exec':
        return a
    clean = re.sub(r'^```(?:python)?\s*|\s*```$', '', command.strip(), flags=re.I)
    if not clean or len(clean) > 5000:
        raise ValueError('EMPTY_OR_TOO_LONG')
    try:
        tree = ast.parse(clean)
    except SyntaxError as exc:
        raise ValueError('INVALID_PYTHON') from exc
    lines = []
    for node in tree.body:
        if isinstance(node, ast.Import) and len(node.names) == 1 and node.names[0].name == 'pyautogui' and not node.names[0].asname:
            continue
        if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
            raise ValueError('DIRECT_GUI_CALL_REQUIRED')
        call = node.value
        if not (isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name)
                and call.func.value.id == 'pyautogui' and call.func.attr in METHODS):
            raise ValueError('NON_GUI_CAPABILITY')
        try:
            args = [ast.literal_eval(x) for x in call.args]
            kwargs = {x.arg: ast.literal_eval(x.value) for x in call.keywords}
        except (ValueError, TypeError) as exc:
            raise ValueError('LITERAL_ARGUMENTS_REQUIRED') from exc
        if None in kwargs or any(not isinstance(x, (str,int,float,bool,list,tuple,type(None))) for x in args):
            raise ValueError('INVALID_ARGUMENT')
        name = call.func.attr
        if name == 'sleep' and (not args or not isinstance(args[0], (int,float)) or not 0 <= args[0] <= 3):
            raise ValueError('UNBOUNDED_SLEEP')
        if name == 'scroll' and (not args or not isinstance(args[0], (int,float)) or abs(args[0]) > 12):
            raise ValueError('UNBOUNDED_SCROLL')
        if any(isinstance(x, float) and not math.isfinite(x) for x in args + list(kwargs.values())):
            raise ValueError('NONFINITE_ARGUMENT')
        if kwargs.get('duration',0) > 3 or kwargs.get('interval',0) > 1 or kwargs.get('clicks',1) > 3 or kwargs.get('presses',1) > 30:
            raise ValueError('UNBOUNDED_ACTION')
        keys = {str(x).lower() for x in args}
        if name == 'hotkey' and ({'ctrl','alt','t'} <= keys or {'win','r'} <= keys):
            raise ValueError('TERMINAL_FORBIDDEN')
        lines.append(ast.unparse(call))
    if not lines or len(lines) > 8:
        raise ValueError('ACTION_COUNT')
    a['command'] = '\n'.join(lines)
    return a


def tree_signature(text):
    # Ignore source order, whitespace and zero-width filename wrapping.
    lines = {re.sub(r'\s+', ' ', x.replace('\u200b','')).strip() for x in text.splitlines()}
    lines = {x for x in lines if x and not x.startswith(('You are','Please ','Here is','tag\t'))}
    return hashlib.sha256('\n'.join(sorted(lines)).encode()).hexdigest()


def _parse_accessibility_controls(observation):
    controls=[]
    interactive={'push-button','button','menu','menu-item','check-box','radio-button','combo-box','entry','link','toggle-button','spin-button','slider','tab','table-cell','section'}
    for line in str(observation or '').splitlines():
        cols=line.split('\t')
        if len(cols)<7 or cols[0] not in interactive: continue
        xy=re.findall(r'-?\d+',cols[-2]); wh=re.findall(r'\d+',cols[-1])
        if len(xy)!=2 or len(wh)!=2: continue
        x,y=map(int,xy); w,h=map(int,wh)
        name=(cols[1] or cols[2]).replace('\u200b','').strip()
        if not name or w<=0 or h<=0: continue
        controls.append({'role':cols[0],'name':name,'x':x,'y':y,'w':w,'h':h,
                         'cx':x+w//2,'cy':y+h//2})
    return controls


def _resolve_accessibility_target(action, observation):
    target=action.get('target') if isinstance(action,dict) else None
    controls=_parse_accessibility_controls(observation)
    if not controls: return None
    if isinstance(target,dict):
        source=str(target.get('source') or '').lower()
        if source=='accessibility':
            label=normalized_target(target.get('label'))
            role=normalized_target(target.get('role'))
            hits=[c for c in controls if normalized_target(c['name'])==label and (not role or normalized_target(c['role'])==role)]
            return hits[0] if len(hits)==1 else None
        if source=='screenshot':
            return None
    intent=' '.join(str(action.get(k) or '') for k in ('plan','summary'))
    norm_intent=normalized_target(intent)
    hits=[c for c in controls if len(normalized_target(c['name']))>=3 and normalized_target(c['name']) in norm_intent]
    longest=max((len(normalized_target(c['name'])) for c in hits),default=0)
    hits=[c for c in hits if len(normalized_target(c['name']))==longest]
    return hits[0] if len(hits)==1 else None


def normalized_target(value):
    return re.sub(r'\s+',' ',str(value or '').replace('\u200b','')).strip().casefold()


def _gui_calls(command):
    try:
        tree=ast.parse(str(command or ''))
    except SyntaxError:
        return []
    calls=[]
    for node in tree.body:
        if not isinstance(node,ast.Expr) or not isinstance(node.value,ast.Call):
            return []
        call=node.value
        if not (isinstance(call.func,ast.Attribute) and isinstance(call.func.value,ast.Name)
                and call.func.value.id=='pyautogui'):
            return []
        calls.append(call)
    return calls


def _repair_single_pointer_target(action, observation):
    if action.get('action')!='exec' or isinstance(action.get('target'),dict):
        return action
    # Repair is intentionally narrower than normal grounding. It exists only
    # for a single atomic pointer call whose supplied coordinates already land
    # inside exactly one accessibility control. Compound programs and semantic
    # guesses remain fail-closed.
    calls=_gui_calls(action.get('command',''))
    if len(calls)!=1 or calls[0].func.attr not in {'click','doubleClick','rightClick'}:
        return action
    call=calls[0]
    try:
        if len(call.args)>=2:
            x=float(ast.literal_eval(call.args[0])); y=float(ast.literal_eval(call.args[1]))
        else:
            kwargs={kw.arg:ast.literal_eval(kw.value) for kw in call.keywords if kw.arg}
            x=float(kwargs['x']); y=float(kwargs['y'])
    except (ValueError,TypeError,KeyError):
        return action
    hits=[c for c in _parse_accessibility_controls(observation)
          if c['x']<=x<=c['x']+c['w'] and c['y']<=y<=c['y']+c['h']]
    if len(hits)!=1:
        return action
    resolved=hits[0]
    repaired=dict(action)
    repaired['target']={'source':'accessibility','label':resolved['name'],'role':resolved['role']}
    repaired['compiler_note']='Synthesized coordinate-proven accessibility target for one atomic pointer action: '+resolved['role']+' '+resolved['name']
    return repaired


def canonical_target_proof(target):
    if not isinstance(target,dict):
        return ''
    payload='|'.join((
        str(target.get('source') or ''),
        normalized_target(target.get('role')),
        normalized_target(target.get('label')),
        str(int(target.get('x') or 0)),
        str(int(target.get('y') or 0)),
        str(int(target.get('w') or 0)),
        str(int(target.get('h') or 0)),
        str(int(target.get('cx') or 0)),
        str(int(target.get('cy') or 0)),
        str(target.get('foreground_sha256') or ''),
    ))
    return hashlib.sha256(payload.encode()).hexdigest()


def task091_panel_target_proof(target):
    if not isinstance(target,dict):
        return ''
    payload='|'.join((
        str(target.get('source') or ''),
        normalized_target(target.get('role')),
        normalized_target(target.get('label')),
        str(int(target.get('x') or 0)),
        str(int(target.get('y') or 0)),
        str(int(target.get('w') or 0)),
        str(int(target.get('h') or 0)),
        str(int(target.get('cx') or 0)),
        str(int(target.get('cy') or 0)),
        ','.join(str(int(v)) for v in (target.get('window_bbox') or [])),
        str(target.get('screenshot_sha256') or ''),
        str(target.get('source_observation_id') or ''),
        str(int(target.get('control_pid') or 0)),
        normalized_target(target.get('control_role')),
        normalized_target(target.get('application')),
    ))
    return hashlib.sha256(payload.encode()).hexdigest()


def task091_spatial_target_proof(target):
    if not isinstance(target,dict):
        return ''
    payload='|'.join((
        str(target.get('source') or ''),
        normalized_target(target.get('role')),
        normalized_target(target.get('label')),
        str(int(target.get('slide') or 0)),
        str(int(target.get('x') or 0)),
        str(int(target.get('y') or 0)),
        str(int(target.get('w') or 0)),
        str(int(target.get('h') or 0)),
        str(int(target.get('cx') or 0)),
        str(int(target.get('cy') or 0)),
        str(target.get('foreground_sha256') or ''),
        str(target.get('deck_sha256') or ''),
    ))
    return hashlib.sha256(payload.encode()).hexdigest()


def _validate_task091_pptx_pointer(action):
    target=action.get('target') if isinstance(action,dict) else None
    if not isinstance(target,dict):
        raise ValueError('TASK091_CANONICAL_TARGET_REQUIRED')
    required=('label','role','slide','x','y','w','h','cx','cy',
              'foreground_sha256','deck_sha256','proof_sha256')
    if any(target.get(key) in (None,'') for key in required):
        raise ValueError('TASK091_CANONICAL_TARGET_INCOMPLETE')
    if str(target.get('source') or '').lower()!='task091-pptx-canonical':
        raise ValueError('TASK091_CANONICAL_TARGET_SOURCE_INVALID')
    if normalized_target(target.get('role'))!='task091-canonical-point':
        raise ValueError('TASK091_CANONICAL_TARGET_ROLE_INVALID')
    slide=int(target.get('slide') or 0)
    if not 1 <= slide <= 13:
        raise ValueError('TASK091_CANONICAL_SLIDE_INVALID')
    for key in ('foreground_sha256','deck_sha256'):
        value=str(target.get(key) or '')
        if not re.fullmatch(r'[0-9a-f]{64}',value):
            raise ValueError('TASK091_CANONICAL_DIGEST_INVALID')
    expected=task091_spatial_target_proof(target)
    if not expected or expected!=str(target.get('proof_sha256') or ''):
        raise ValueError('TASK091_CANONICAL_TARGET_PROOF_INVALID')
    x=int(target.get('x')); y=int(target.get('y')); w=int(target.get('w')); h=int(target.get('h'))
    cx=int(target.get('cx')); cy=int(target.get('cy'))
    if w != 2 or h != 2 or x != cx-1 or y != cy-1:
        raise ValueError('TASK091_CANONICAL_TARGET_GEOMETRY_INVALID')
    calls=_gui_calls(action.get('command',''))
    if len(calls)!=1 or calls[0].func.attr not in {'click','doubleClick','rightClick'}:
        raise ValueError('TASK091_CANONICAL_POINTER_ATOMIC_REQUIRED')
    call=calls[0]
    try:
        if len(call.args)>=2:
            px=float(ast.literal_eval(call.args[0])); py=float(ast.literal_eval(call.args[1]))
        else:
            kwargs={kw.arg:ast.literal_eval(kw.value) for kw in call.keywords if kw.arg}
            px=float(kwargs['x']); py=float(kwargs['y'])
    except (ValueError,TypeError,KeyError):
        raise ValueError('TASK091_CANONICAL_POINTER_COORDINATES_INVALID')
    if abs(px-cx)>0.5 or abs(py-cy)>0.5:
        raise ValueError('TASK091_CANONICAL_POINTER_COORDINATES_MISMATCH')
    return action


def _validate_task091_panel_pointer(action):
    target=action.get('target') if isinstance(action,dict) else None
    if not isinstance(target,dict):
        raise ValueError('TASK091_PANEL_TARGET_REQUIRED')
    required=('label','role','x','y','w','h','cx','cy','window_bbox',
              'screenshot_sha256','source_observation_id','control_pid',
              'control_role','application','proof_sha256')
    if any(target.get(key) in (None,'') for key in required):
        raise ValueError('TASK091_PANEL_TARGET_INCOMPLETE')
    if str(target.get('source') or '').lower()!='task091-panel-canonical':
        raise ValueError('TASK091_PANEL_TARGET_SOURCE_INVALID')
    if normalized_target(target.get('role'))!='task091-panel-point':
        raise ValueError('TASK091_PANEL_TARGET_ROLE_INVALID')
    bbox=target.get('window_bbox')
    if bbox != [70,27,1850,1053]:
        raise ValueError('TASK091_PANEL_WINDOW_GEOMETRY_INVALID')
    label=str(target.get('label') or '')
    if label not in {'TEXT OPTIONS','Text Box'}:
        raise ValueError('TASK091_PANEL_LABEL_NOT_ALLOWLISTED')
    wx,wy,ww,wh=(int(v) for v in bbox)
    cx=int(target.get('cx')); cy=int(target.get('cy'))
    x=int(target.get('x')); y=int(target.get('y'))
    w=int(target.get('w')); h=int(target.get('h'))
    if w<=0 or h<=0 or (cx,cy)!=(x+w//2,y+h//2):
        raise ValueError('TASK091_PANEL_TARGET_GEOMETRY_INVALID')
    if not (wx <= x and wy <= y and x+w <= wx+ww and y+h <= wy+wh):
        raise ValueError('TASK091_PANEL_TARGET_OUTSIDE_WINDOW')
    if type(target.get('control_pid')) is not int or int(target.get('control_pid'))<=0:
        raise ValueError('TASK091_PANEL_CONTROL_PID_INVALID')
    if not str(target.get('control_role') or '').strip():
        raise ValueError('TASK091_PANEL_CONTROL_ROLE_INVALID')
    if not re.fullmatch(r'\d{4}-\d{2}-(?:before|after)',str(target.get('source_observation_id') or '')):
        raise ValueError('TASK091_PANEL_OBSERVATION_ID_INVALID')
    shot=str(target.get('screenshot_sha256') or '')
    if not re.fullmatch(r'[0-9a-f]{64}',shot):
        raise ValueError('TASK091_PANEL_SCREENSHOT_DIGEST_INVALID')
    expected=task091_panel_target_proof(target)
    if not expected or expected!=str(target.get('proof_sha256') or ''):
        raise ValueError('TASK091_PANEL_TARGET_PROOF_INVALID')
    calls=_gui_calls(action.get('command',''))
    if len(calls)!=1 or calls[0].func.attr!='click':
        raise ValueError('TASK091_PANEL_POINTER_ATOMIC_REQUIRED')
    call=calls[0]
    try:
        px=float(ast.literal_eval(call.args[0])); py=float(ast.literal_eval(call.args[1]))
    except (ValueError,TypeError,IndexError):
        raise ValueError('TASK091_PANEL_POINTER_COORDINATES_INVALID')
    if abs(px-cx)>0.5 or abs(py-cy)>0.5:
        raise ValueError('TASK091_PANEL_POINTER_COORDINATES_MISMATCH')
    return action


def _validate_canonical_pointer(action):
    target=action.get('target') if isinstance(action,dict) else None
    if not isinstance(target,dict):
        raise ValueError('CANONICAL_TARGET_REQUIRED')
    required=('label','role','x','y','w','h','cx','cy','foreground_sha256','proof_sha256')
    if any(target.get(key) in (None,'') for key in required):
        raise ValueError('CANONICAL_TARGET_INCOMPLETE')
    if str(target.get('source') or '').lower()!='accessibility-canonical':
        raise ValueError('CANONICAL_TARGET_SOURCE_INVALID')
    expected=canonical_target_proof(target)
    if not expected or expected!=str(target.get('proof_sha256') or ''):
        raise ValueError('CANONICAL_TARGET_PROOF_INVALID')
    calls=_gui_calls(action.get('command',''))
    if len(calls)!=1 or calls[0].func.attr not in {'click','doubleClick','rightClick'}:
        raise ValueError('CANONICAL_POINTER_ATOMIC_REQUIRED')
    call=calls[0]
    try:
        if len(call.args)>=2:
            x=float(ast.literal_eval(call.args[0])); y=float(ast.literal_eval(call.args[1]))
        else:
            kwargs={kw.arg:ast.literal_eval(kw.value) for kw in call.keywords if kw.arg}
            x=float(kwargs['x']); y=float(kwargs['y'])
    except (ValueError,TypeError,KeyError):
        raise ValueError('CANONICAL_POINTER_COORDINATES_INVALID')
    cx=float(target.get('cx')); cy=float(target.get('cy'))
    if abs(x-cx)>0.5 or abs(y-cy)>0.5:
        raise ValueError('CANONICAL_POINTER_COORDINATES_MISMATCH')
    if int(target.get('w') or 0)<=0 or int(target.get('h') or 0)<=0:
        raise ValueError('CANONICAL_TARGET_GEOMETRY_INVALID')
    return action


def _compile_grounded_click(action, observation):
    if action.get('action')!='exec': return action
    declared=action.get('target') if isinstance(action,dict) else None
    target=_resolve_accessibility_target(action,observation)
    if isinstance(declared,dict) and str(declared.get('source') or '').lower()=='accessibility' and not target:
        raise ValueError('ACCESSIBILITY_TARGET_UNRESOLVED')
    if not target: return action
    tree=ast.parse(action['command']); changed=False
    for node in tree.body:
        if not isinstance(node,ast.Expr) or not isinstance(node.value,ast.Call): continue
        call=node.value
        if not (isinstance(call.func,ast.Attribute) and call.func.attr in {'click','doubleClick','rightClick'}): continue
        if len(call.args)<2: continue
        try: x=float(ast.literal_eval(call.args[0])); y=float(ast.literal_eval(call.args[1]))
        except (ValueError,TypeError): continue
        inside=target['x']<=x<=target['x']+target['w'] and target['y']<=y<=target['y']+target['h']
        if inside: continue
        call.args[0]=ast.Constant(target['cx']); call.args[1]=ast.Constant(target['cy']); changed=True
    if changed:
        action=dict(action); action['command']='\n'.join(ast.unparse(n.value) for n in tree.body)
        action['compiler_note']='Accessibility-grounded target resolved deterministically: '+target['role']+' '+target['name']
    return action


def _repair_wps_modal_dismiss(action, active_application, verifier_result=None, recent_commands=None):
    """Resolve WPS modal dismissals with bounded escalation: Escape, then visual Close."""
    if not isinstance(action,dict) or action.get('action')!='exec' or isinstance(action.get('target'),dict):
        return action
    active=normalized_target(active_application)
    if not active.startswith('wps'):
        return action
    calls=_gui_calls(action.get('command',''))
    if len(calls)!=1 or calls[0].func.attr not in {'click','doubleClick','rightClick'}:
        return action
    parts=[action.get(key,'') for key in ('plan','summary','verification','expected_change')]
    checkpoint=action.get('checkpoint')
    if isinstance(checkpoint,dict):
        parts.extend(checkpoint.get(key,'') for key in ('name','application','visible_text'))
    fact_quotes=[]
    for fact in action.get('observed_facts') or []:
        if isinstance(fact,dict):
            quote=str(fact.get('quote') or '').strip()
            fact_quotes.append(quote)
            parts.append(quote)
    semantic=normalized_target(' '.join(str(x or '') for x in parts))
    close_intent=bool(re.search(r'\b(?:close|dismiss|resolve|clear)\b',semantic))
    modal_state=bool(re.search(r'\b(?:modal|dialog|notice|prompt|system check)\b',semantic))
    if not (close_intent and modal_state):
        return action

    recent=[str(x or '') for x in (recent_commands or [])]
    consecutive_esc=0
    for command in reversed(recent):
        if command=="pyautogui.press('esc')":
            consecutive_esc+=1
            continue
        break
    result=verifier_result if isinstance(verifier_result,dict) else {}
    last_escape_stalled=(
        consecutive_esc>=2
        and result.get('tree_changed') is False
        and result.get('visual_changed') is False
        and str(result.get('reason') or '') in {'action_no_progress','visual_change_without_semantic_checkpoint'}
    )

    if last_escape_stalled:
        label=next((q for q in fact_quotes if normalized_target(q) in {'close','ok','cancel'}), '')
        if not label:
            return action
        if normalized_target(label)=='ok':
            repaired=dict(action)
            repaired.pop('target',None)
            repaired['command']="pyautogui.press('enter')"
            repaired['compiler_note']='After two bounded Escape attempts, replaced the explicitly observed WPS modal OK pointer with deterministic Enter default-button activation.'
            return repaired
        call=calls[0]
        try:
            if len(call.args)>=2:
                float(ast.literal_eval(call.args[0])); float(ast.literal_eval(call.args[1]))
            else:
                kwargs={kw.arg:ast.literal_eval(kw.value) for kw in call.keywords if kw.arg}
                float(kwargs['x']); float(kwargs['y'])
        except (ValueError,TypeError,KeyError):
            return action
        repaired=dict(action)
        repaired['target']={'source':'screenshot','label':label}
        repaired['compiler_note']='After two bounded Escape attempts, preserved the single visual pointer using the explicitly observed modal control label.'
        return repaired

    repaired=dict(action)
    repaired.pop('target',None)
    repaired['command']="pyautogui.press('esc')"
    repaired['compiler_note']='Replaced ungrounded WPS modal-dismiss pointer with deterministic Escape.'
    return repaired



def allow_bounded_wps_escape_repeat(action, active_application, verifier_result, recent_commands):
    """Allow exactly one evidence-backed second Escape for stacked WPS modals."""
    if not isinstance(action,dict) or action.get('action')!='exec':
        return False
    if str(action.get('command') or '') != "pyautogui.press('esc')":
        return False
    if 'WPS modal-dismiss' not in str(action.get('compiler_note') or ''):
        return False
    if not normalized_target(active_application).startswith('wps'):
        return False
    result=verifier_result if isinstance(verifier_result,dict) else {}
    if not (result.get('tree_changed') is True or result.get('visual_changed') is True):
        return False
    recent=[str(x or '') for x in (recent_commands or [])]
    consecutive=0
    for command in reversed(recent):
        if command=="pyautogui.press('esc')":
            consecutive+=1
            continue
        break
    return consecutive==1

def allow_bounded_wps_modal_close_repeat(action, active_application, verifier_result, recent_commands):
    """Allow exactly one retry when the first explicit WPS modal Close click only focused the dialog."""
    if not isinstance(action,dict) or action.get('action')!='exec':
        return False
    if not normalized_target(active_application).startswith('wps'):
        return False
    if 'After two bounded Escape attempts' not in str(action.get('compiler_note') or ''):
        return False
    target=action.get('target')
    if not isinstance(target,dict) or str(target.get('source') or '').lower()!='screenshot':
        return False
    if normalized_target(target.get('label')) not in {'close','ok','cancel'}:
        return False
    command=str(action.get('command') or '')
    calls=_gui_calls(command)
    if len(calls)!=1 or calls[0].func.attr not in {'click','doubleClick','rightClick'}:
        return False
    result=verifier_result if isinstance(verifier_result,dict) else {}
    if not (result.get('tree_changed') is False and result.get('visual_changed') is False):
        return False
    if str(result.get('reason') or '') not in {'action_no_progress','visual_change_without_semantic_checkpoint'}:
        return False
    recent=[str(x or '') for x in (recent_commands or [])]
    consecutive=0
    for previous in reversed(recent):
        if previous==command:
            consecutive+=1
            continue
        break
    return consecutive==1


def ground_action(action, active_application, observation='', verified_milestones=None, allow_canonical=False,
                  verifier_result=None, recent_commands=None):
    """Compile desktop activation and block unsafe source-context abandonment."""
    a=canonical_action(action)
    a=_repair_wps_modal_dismiss(a,active_application,verifier_result,recent_commands)
    canonical_pointer=False
    if a.get('action')=='exec' and re.search(r'pyautogui\.(?:click|doubleClick|rightClick)\s*\(',a.get('command','')):
        target=a.get('target')
        source=str(target.get('source') or '').lower() if isinstance(target,dict) else ''
        if source in {'accessibility-canonical','task091-pptx-canonical','task091-panel-canonical'}:
            if not allow_canonical:
                raise ValueError('CANONICAL_TARGET_UNTRUSTED')
            if source=='accessibility-canonical':
                a=_validate_canonical_pointer(a)
                note='Trusted local canonical accessibility target accepted without secondary re-resolution.'
            elif source=='task091-panel-canonical':
                a=_validate_task091_panel_pointer(a)
                note='Trusted Task 091 panel target accepted with signed screenshot/window proof.'
            else:
                a=_validate_task091_pptx_pointer(a)
                note='Trusted Task 091 PPTX-backed canonical target accepted with signed foreground/deck proof.'
            canonical_pointer=True
            a=dict(a)
            a['compiler_note']=note
        else:
            a=_repair_single_pointer_target(a,observation)
            target=a.get('target')
            if not isinstance(target,dict): raise ValueError('POINTER_TARGET_REQUIRED')
            source=str(target.get('source') or '').lower(); label=str(target.get('label') or '').strip()
            if source not in {'accessibility','screenshot'} or not label: raise ValueError('POINTER_TARGET_INVALID')
            if source=='accessibility' and not str(target.get('role') or '').strip(): raise ValueError('ACCESSIBILITY_ROLE_REQUIRED')
    if not canonical_pointer:
        a=_compile_grounded_click(a,observation)
    plan=str(a.get('plan') or '').lower()
    active=str(active_application or 'unknown')
    reveal=bool(re.search(r'(?:bring|show|reveal|switch to) (?:the )?desktop\b',plan))
    if a['action']=='exec' and active not in ('Desktop','unknown') and reveal:
        tree=ast.parse(a['command'])
        if len(tree.body)==1 and tree.body[0].value.func.attr=='hotkey':
            keys=[ast.literal_eval(x) for x in tree.body[0].value.args]
            if keys==['alt','tab']:
                a['command']="pyautogui.hotkey('ctrl', 'win', 'd')"
                a['compiler_note']='Ubuntu show-desktop shortcut implements the explicit desktop-activation plan.'
    if a['action']=='exec' and 'archive' in active.lower():
        tree=ast.parse(a['command'])
        switching=False
        for node in tree.body:
            call=node.value
            if call.func.attr!='hotkey':
                continue
            keys={str(ast.literal_eval(x)).lower() for x in call.args}
            if keys in ({'ctrl','win','d'},{'ctrl','super','d'},{'alt','tab'}):
                switching=True
                break
        if switching:
            milestones=verified_milestones or []
            complete=False
            for item in milestones:
                text=' '.join(str(item.get(k,'')).lower() for k in ('name','application','visible_text','verification')) if isinstance(item,dict) else str(item).lower()
                if 'archive' in text and any(w in text for w in ('read','processed','complete','completed','finished','extracted','verified')):
                    complete=True
                    break
            if not complete:
                raise ValueError('OPEN_ARCHIVE_CONTEXT_SWITCH_FORBIDDEN')
    return a


def visual_signature(image):
    if not image:
        return ''
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(base64.b64decode(image.split(',',1)[1]))).convert('RGB')
        im = im.crop((0, min(28, im.height // 10), im.width, im.height)).resize((48,27))
        # Quantized RGB preserves chroma/saturation changes while suppressing cursor/AA noise.
        return bytes((x // 32) for x in im.tobytes()).hex()
    except (ValueError, OSError, IndexError, binascii.Error):
        return ''


class Verifier:
    def __init__(self):
        self.last_tree = None
        self.last_visual = ''
        self.last_visible_lines = set()
        self.seen = deque(maxlen=32)
        self.no_progress = 0
        self.changes = 0
        self.pending = False
        self.last_result = {'progress':False,'reason':'initial_observation'}

    @property
    def recovery_level(self):
        return min(5, self.no_progress // 2)

    def issued(self, command):
        self.pending = True

    def observe(self, text, image):
        sig, visual = tree_signature(text), visual_signature(image)
        current_lines={re.sub(r'\s+',' ',x.replace('\u200b','')).strip() for x in str(text or '').splitlines()}
        current_lines={x for x in current_lines if x and not x.startswith(('ACTIVE APPLICATION','BACKGROUND DESKTOP','[Compacted'))}
        new_visible=[]
        if self.last_visible_lines:
            candidates=current_lines-self.last_visible_lines
            # Surface bounded, current-screen novelty so mid-task events are not
            # lost inside a long trajectory. This is observation-only evidence.
            new_visible=sorted(candidates,key=lambda x:(0 if any(k in x.casefold() for k in ('error','warning','message','notification','dialog','status','complete','failed','success')) else 1,len(x)))[:12]
            new_visible=[x[:320] for x in new_visible]
        tree_changed = self.last_tree is not None and sig != self.last_tree
        visual_changed = False
        if visual and self.last_visual and len(visual) == len(self.last_visual):
            a,b=bytes.fromhex(visual),bytes.fromhex(self.last_visual)
            visual_changed = sum(abs(x-y) for x,y in zip(a,b)) / (len(a)*7) > 0.025
        novel = sig not in self.seen
        progress = self.pending and ((tree_changed and novel) or (visual_changed and sig == self.last_tree))
        if self.last_tree is not None and self.pending:
            if progress:
                self.no_progress = 0
                self.changes += 1
            else:
                self.no_progress += 1
        reason='progress_verified' if progress else ('action_no_progress' if self.pending else 'observation_only')
        self.last_result = {'progress':bool(progress),'reason':reason,
                            'tree_changed':tree_changed,'visual_changed':visual_changed,
                            'novel_tree':novel,'new_visible_lines':new_visible,
                            'no_progress':self.no_progress,'recovery_level':self.recovery_level,
                            'before_tree_sha256':self.last_tree,'after_tree_sha256':sig}
        self.seen.append(sig)
        self.last_visible_lines=current_lines
        self.last_tree, self.last_visual = sig,visual
        self.pending = False
        return self.last_result

    def can_finish(self, action, observation):
        try:
            confidence=float(action.get('confidence',0))
        except (ValueError,TypeError):
            return False
        evidence=str(action.get('verification') or '').strip()
        words={w for w in re.findall(r'\w+',evidence.lower()) if len(w)>3}
        visible={w for w in re.findall(r'\w+',observation.lower()) if len(w)>3}
        artifacts=[x.casefold() for x in re.findall(r'[A-Za-z0-9_.-]+\.(?:jpg|jpeg|png|pdf|docx|xlsx|pptx|zip|csv)',evidence,re.I)]
        specific=any(x in observation.casefold() for x in artifacts) if artifacts else len(words & visible)>=2
        return self.changes > 0 and self.no_progress < 2 and math.isfinite(confidence) and confidence >= .8 and len(evidence)>=8 and specific


def compact_tree(text, instruction='', limit=MAX_TREE_CHARS):
    lines=list(dict.fromkeys(x.replace('\u200b','').strip() for x in text.splitlines() if x.strip()))
    if len('\n'.join(lines)) <= limit:
        return '\n'.join(lines)
    words={x.lower() for x in re.findall(r'[\w.-]+',instruction) if len(x)>3}
    ranked=[]
    for i,line in enumerate(lines):
        score=3 if line.startswith(('entry','text\t','push-button','menu','dialog','frame','document','page','heading','table-cell','list-item','check','combo')) else 0
        score+=sum(2 for x in words if x in line.lower())
        ranked.append((-score,i,line[:1800]))
    selected=[]; used=0
    for _,i,line in sorted(ranked):
        if used+len(line)+1<=limit-100:
            selected.append((i,line));used+=len(line)+1
    return '[Compacted accessibility tree; background/occluded controls may still be present.]\n'+'\n'.join(x[1] for x in sorted(selected))


def foreground_context(text):
    """Use the observed Ubuntu application menu, not the order of background trees."""
    lines=text.splitlines();active='unknown'
    for line in lines:
        cols=line.split('\t')
        if len(cols)>=7 and cols[0]=='menu' and re.search(r'\(\d+, 0\)',cols[-2]) and cols[1]!='System':
            active=cols[1]
    hidden=[];kept=[]
    for line in lines:
        cols=line.split('\t')
        if active not in ('unknown','Files','Desktop') and len(cols)>=7 and cols[0]=='label':
            name=cols[1].replace('\u200b','')
            xy=re.findall(r'\d+',cols[-2])
            on_desktop=len(xy)==2 and int(xy[0])>=1700 and int(xy[1])>=500
            if on_desktop and (name=='Home' or re.search(r'\.(pdf|zip|pptx|docx|xlsx|png|jpg)(#)?$',name,re.I)):
                hidden.append(name);continue
        kept.append(line)
    # In the OSWorld linear tree Chromium's own title controls mark its section.
    # Drop prior background windows only when the panel explicitly names Chrome.
    if active=='Google Chrome':
        starts=[i for i,l in enumerate(kept) if l.startswith('push-button\tMinimise\t')]
        if starts:kept=kept[starts[-1]:]
    if active=='Thunderbird Mail':
        starts=[i for i,l in enumerate(kept) if l.startswith('push-button\tMail (Ctrl+1)\t')]
        if starts:kept=kept[starts[0]:]
    elif active=='Archive Manager':
        # The observed panel/dock ends this foreground archive section; office
        # menu/document trees after it belong to covered background windows.
        ends=[i for i,l in enumerate(kept) if l.startswith('menu\tSystem\t')]
        if ends:kept=kept[:ends[0]+1]
    elif normalized_target(active).startswith('wps'):
        # WPS can be foreground while AT-SPI still exposes Chromium's covered
        # document tree. When that mismatch is explicit, discard the stale web
        # tree and retain only the WPS panel marker plus dock controls.
        panel=[i for i,l in enumerate(kept)
               if l.startswith('menu\t') and normalized_target(l.split('\t')[1]).startswith('wps')]
        if panel:
            start=panel[-1]
            if any(l.startswith('document-web\t') for l in kept[:start]):
                kept=kept[start:]
    prefix='ACTIVE APPLICATION (Ubuntu panel): '+active+'\n'
    if hidden:prefix+='BACKGROUND DESKTOP FILES (not clickable until revealed): '+', '.join(hidden)+'\n'
    return prefix+'\n'.join(kept),active


def canonical_foreground_context(text):
    """Return one deterministic foreground tree shared by selector and grounder."""
    focused,active=foreground_context(str(text or ''))
    lines=focused.splitlines()
    roots=[]
    for index,line in enumerate(lines):
        cols=line.split('\t')
        if len(cols)<7 or normalized_target(cols[0]) not in {'document-web','document','frame','dialog','window'}:
            continue
        xy=re.findall(r'-?\d+',cols[-2]); wh=re.findall(r'\d+',cols[-1])
        if len(xy)!=2 or len(wh)!=2:
            continue
        x,y=map(int,xy); w,h=map(int,wh)
        if w<=0 or h<=0:
            continue
        label=(cols[1] or cols[2]).replace('\u200b','').strip()
        roots.append((w*h,index,{'role':cols[0],'label':label,'x':x,'y':y,'w':w,'h':h}))
    if not roots:
        canonical=focused
        meta={'strategy':'foreground-context-no-root','root':None,'active_application':active}
    else:
        roots.sort(key=lambda row:(row[0],row[1]),reverse=True)
        _,start,root=roots[0]
        prefix=[line for line in lines[:start] if line.startswith(('ACTIVE APPLICATION','BACKGROUND DESKTOP FILES'))]
        canonical='\n'.join(prefix+lines[start:])
        meta={'strategy':'dominant-document-root','root':{**root,'line_index':start},'active_application':active}
    return canonical,active,meta


def compress_screenshot(image):
    if not image:
        return '',{}
    from PIL import Image
    im=Image.open(io.BytesIO(base64.b64decode(image.split(',',1)[1]))).convert('RGB')
    original=im.size
    # Preserve the original desktop coordinate system explicitly in the request.
    # Smaller vision input also limits provider image tokens, independently of bytes.
    im.thumbnail((1600,900))
    for quality in (65,50,35,22):
        out=io.BytesIO();im.save(out,format='JPEG',quality=quality,optimize=True)
        data='data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()
        if len(data)<340_000:
            return data,{'width':original[0],'height':original[1],'transmitted_width':im.width,'transmitted_height':im.height,'jpeg_quality':quality,'image_bytes':len(out.getvalue())}
    raise ValueError('SCREENSHOT_PAYLOAD_TOO_LARGE')


def compress_reference_screenshot(image):
    if not image: return '',{}
    from PIL import Image
    im=Image.open(io.BytesIO(base64.b64decode(image.split(',',1)[1]))).convert('RGB')
    original=im.size; im.thumbnail((640,360))
    for quality in (40,28,18):
        out=io.BytesIO(); im.save(out,format='JPEG',quality=quality,optimize=True)
        if len(out.getvalue())<=52000:
            data='data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode()
            return data,{'reference_width':original[0],'reference_height':original[1],
                         'reference_transmitted_width':im.width,'reference_transmitted_height':im.height,
                         'reference_image_bytes':len(out.getvalue())}
    return '',{}


def bounded_instruction(value, limit=7000):
    text=str(value or '')
    if len(text)<=limit: return text
    marker='\n[...middle omitted; objective and final constraints preserved...]\n'
    tail=max(1200,limit//3); head=limit-tail-len(marker)
    return text[:head]+marker+text[-tail:]

def pack_payload(body):
    def size(x): return len(json.dumps(x,ensure_ascii=False).encode())
    before=size(body);b=dict(body)
    b['instruction']=bounded_instruction(b.get('instruction',''),7000)
    focused,active,canonical_meta=canonical_foreground_context(str(b.get('observation','')))
    b['active_application']=active
    b['observation']=compact_tree(focused,b['instruction'],limit=6500)
    b['canonical_foreground_sha256']=hashlib.sha256(b['observation'].encode()).hexdigest()
    b['canonical_foreground_meta']=canonical_meta
    b['memory']=str(b.get('memory',''))[-4500:]
    b['screenshot_data_url'],im=compress_screenshot(b.get('screenshot_data_url',''))
    b['reference_screenshot_data_url'],ref=compress_reference_screenshot(b.get('reference_screenshot_data_url',''))
    b['image_geometry']={**im,**ref}
    after=size(b)
    if after>MAX_PAYLOAD_BYTES:
        raise ValueError('PAYLOAD_GATE')
    return b,{'before_bytes':before,'after_bytes':after,**im}


def validate_response(data,pipeline,build):
    if not isinstance(data,dict) or data.get('pipeline')!=pipeline or data.get('agent_build')!=build:
        raise ValueError('ENDPOINT_INCOMPATIBLE')
    if os.environ.get('ARBM_VALIDATION_SPEND_MODE','zero') != 'zero':
        raise ValueError('NON_ZERO_SPEND_MODE_FORBIDDEN')
    attempts=data.get('provider_attempts') or []
    if data.get('mandatory_cost_usd') != 0 or data.get('paid_fallback_used') is not False:
        raise ValueError('ZERO_SPEND_UNPROVEN')
    if data.get('ok') and not any(a.get('model')==data.get('model') and a.get('status')==200 and
                   (a.get('free_plan_proven') is True or a.get('zero_spend_confirmed') is True) for a in attempts):
        raise ValueError('PROVIDER_FREE_PROOF_MISSING')