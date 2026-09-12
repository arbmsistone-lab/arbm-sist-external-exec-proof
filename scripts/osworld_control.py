"""Local action compiler, observation verifier and bounded payload builder.

This module has no network access and never reads the guest filesystem.
"""
import ast
import base64
import hashlib
import io
import json
import math
import re
from collections import deque

MAX_PAYLOAD_BYTES = 420_000
MAX_TREE_CHARS = 9000
METHODS = {'click','doubleClick','rightClick','moveTo','press','hotkey','write','typewrite',
           'scroll','sleep','mouseDown','mouseUp','dragTo','keyDown','keyUp'}


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


def ground_action(action, active_application, observation='', verified_milestones=None):
    """Compile desktop activation and block unsafe source-context abandonment."""
    a=canonical_action(action)
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
        im = Image.open(io.BytesIO(base64.b64decode(image.split(',',1)[1]))).convert('L')
        im = im.crop((0, min(28, im.height // 10), im.width, im.height)).resize((64,36))
        # Quantization removes antialiasing/cursor noise from the observation identity.
        return bytes((x // 32) for x in im.tobytes()).hex()
    except Exception:
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
        return self.changes > 0 and self.no_progress < 3 and math.isfinite(confidence) and confidence >= .8 and len(evidence)>=8 and bool(words & visible)


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


def pack_payload(body):
    def size(x): return len(json.dumps(x,ensure_ascii=False).encode())
    before=size(body);b=dict(body)
    b['instruction']=str(b.get('instruction',''))[:7000]
    focused,active=foreground_context(str(b.get('observation','')))
    b['active_application']=active
    b['observation']=compact_tree(focused,b['instruction'],limit=6500)
    b['memory']=str(b.get('memory',''))[-4500:]
    b['screenshot_data_url'],im=compress_screenshot(b.get('screenshot_data_url',''))
    b['image_geometry']=im
    after=size(b)
    if after>MAX_PAYLOAD_BYTES:
        raise ValueError('PAYLOAD_GATE')
    return b,{'before_bytes':before,'after_bytes':after,**im}


def validate_response(data,pipeline,build):
    if not isinstance(data,dict) or data.get('pipeline')!=pipeline or data.get('agent_build')!=build:
        raise ValueError('ENDPOINT_INCOMPATIBLE')
    if data.get('mandatory_cost_usd') != 0 or data.get('paid_fallback_used') is not False:
        raise ValueError('ZERO_SPEND_UNPROVEN')
    if data.get('ok'):
        attempts=data.get('provider_attempts') or []
        if not any(a.get('model')==data.get('model') and a.get('status')==200 and
                   (a.get('free_plan_proven') is True or a.get('zero_spend_confirmed') is True) for a in attempts):
            raise ValueError('PROVIDER_FREE_PROOF_MISSING')
