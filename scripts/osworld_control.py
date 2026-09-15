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
    interactive={'push-button','button','menu','menu-item','check-box','radio-button','combo-box','entry','link','toggle-button','spin-button','slider','tab'}
    for line in str(observation or '').splitlines():
        cols=line.split('\t')
        if len(cols)<7 or cols[0] not in interactive: continue
        xy=re.findall(r'-?\d+',cols[-2]); wh=re.findall(r'\d+',cols[-1])
        if len(xy)!=2 or len(wh)!=2: continue
        x,y=map(int,xy); w,h=map(int,wh)
        name=cols[1].replace('\u200b','').strip()
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


def _pointer_calls(command):
    try:
        tree=ast.parse(str(command or ''))
    except SyntaxError:
        return []
    calls=[]
    for node in tree.body:
        if not isinstance(node,ast.Expr) or not isinstance(node.value,ast.Call):
            continue
        call=node.value
        if isinstance(call.func,ast.Attribute) and call.func.attr in {'click','doubleClick','rightClick'}:
            calls.append(call)
    return calls


def _repair_single_pointer_target(action, observation):
    if action.get('action')!='exec' or isinstance(action.get('target'),dict):
        return action
    # Fail closed for compound pointer programs.  Only one atomic pointer action
    # may inherit a target, and only when plan/summary resolves one unique
    # accessibility control in the current foreground observation.
    if len(_pointer_calls(action.get('command','')))!=1:
        return action
    resolved=_resolve_accessibility_target(action,observation)
    if not resolved:
        return action
    repaired=dict(action)
    repaired['target']={'source':'accessibility','label':resolved['name'],'role':resolved['role']}
    repaired['compiler_note']='Synthesized unique accessibility target for one atomic pointer action: '+resolved['role']+' '+resolved['name']
    return repaired


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

def ground_action(action, active_application, observation='', verified_milestones=None):
    """Compile desktop activation and block unsafe source-context abandonment."""
    a=canonical_action(action)
    if a.get('action')=='exec' and re.search(r'pyautogui\.(?:click|doubleClick|rightClick)\s*\(',a.get('command','')):
        a=_repair_single_pointer_target(a,observation)
        target=a.get('target')
        if not isinstance(target,dict): raise ValueError('POINTER_TARGET_REQUIRED')
        source=str(target.get('source') or '').lower(); label=str(target.get('label') or '').strip()
        if source not in {'accessibility','screenshot'} or not label: raise ValueError('POINTER_TARGET_INVALID')
        if source=='accessibility' and not str(target.get('role') or '').strip(): raise ValueError('ACCESSIBILITY_ROLE_REQUIRED')
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
        self.last_result = {'progress':bool(progress),'tree_changed':tree_changed,'visual_changed':visual_changed,
                            'novel_tree':novel,'no_progress':self.no_progress,'recovery_level':self.recovery_level,
                            'before_tree_sha256':self.last_tree,'after_tree_sha256':sig}
        self.seen.append(sig)
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
    prefix='ACTIVE APPLICATION (Ubuntu panel): '+active+'\n'
    if hidden:prefix+='BACKGROUND DESKTOP FILES (not clickable until revealed): '+', '.join(hidden)+'\n'
    return prefix+'\n'.join(kept),active


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
    focused,active=foreground_context(str(b.get('observation','')))
    b['active_application']=active
    b['observation']=compact_tree(focused,b['instruction'],limit=6500)
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
