import base64
import hashlib
import json
import os
import time
from openai import OpenAI
from mm_agents.gemini_action_parser import InvalidActionError, convert_to_pyautogui_action
from mm_agents.g3_paid_control import gui_action_violation

MODEL = os.environ.get('ARBM_G3_FREE_MODEL', 'dots-studio/dots-3-note-preview:free')
if not MODEL.endswith(':free'):
    raise RuntimeError('G3_FREE_MODEL_REQUIRED')

def obj(properties=None, required=None):
    schema={'type':'object','properties':properties or {}}
    if required: schema['required']=required
    return schema

def integer(description): return {'type':'integer','description':description}
def string(description): return {'type':'string','description':description}
X=integer('Normalized x coordinate from 0 to 1000.')
Y=integer('Normalized y coordinate from 0 to 1000.')
POINT=obj({'x':X,'y':Y},['x','y'])

def tool(name, description, parameters=None):
    f={'name':name,'description':description}
    if parameters is not None: f['parameters']=parameters
    return {'type':'function','function':f}
TOOLS=[
    tool('click','Left-click at a coordinate.',POINT),
    tool('double_click','Double-click at a coordinate.',POINT),
    tool('right_click','Right-click at a coordinate.',POINT),
    tool('move','Move the pointer to a coordinate.',POINT),
    tool('type','Type text.',obj({'text':string('Text to type.'),'press_enter':{'type':'boolean'}},['text'])),
    tool('drag_and_drop','Drag between coordinates.',obj({'start_x':X,'start_y':Y,'end_x':X,'end_y':Y},['start_x','start_y','end_x','end_y'])),
    tool('scroll','Scroll at a coordinate.',obj({'x':X,'y':Y,'direction':string('up, down, left, or right'),'magnitude_in_wheel_clicks':integer('Wheel clicks')},['x','y','direction'])),
    tool('wait','Wait briefly.',obj({'seconds':{'type':'number','minimum':0,'maximum':2}})),
    tool('press_key','Press and release one key.',obj({'key':string('PyAutoGUI key')},['key'])),
    tool('hotkey','Press a keyboard shortcut.',obj({'keys':{'type':'array','items':{'type':'string'}}},['keys'])),
    tool('take_screenshot','Take a fresh screenshot.'),
    tool('done','Signal that the task is complete.'),
    tool('infeasible','Signal that the task cannot be completed.')
]

SYSTEM='''You control an OSWorld Ubuntu virtual desktop. Use only the declared GUI tools.
Coordinates are normalized 0..1000. Never open a terminal, run shell commands, install packages,
or type shell/PowerShell commands. Continue from the current screenshot and avoid repeating an
action when the screen did not change. Use done only after the requested end state is complete.
Return at most one executable tool call per turn.'''

class ArbmG3Agent:
    def __init__(self, model=None, max_tokens=None, top_p=None, temperature=None,
                 action_space='pyautogui', observation_type='screenshot',
                 max_trajectory_length=None, client_password='', **kwargs):
        key=os.environ.get('OPENROUTER_API_KEY','').strip()
        if not key: raise RuntimeError('OPENROUTER_API_KEY_MISSING')
        self.model_id=MODEL
        self.client=OpenAI(base_url='https://openrouter.ai/api/v1',api_key=key,timeout=45,max_retries=0)
        self.task_current_date=None
        self.messages=[]
        self._instruction=''
        self._last_screen=None
        self._same_screen_steps=0
        self._call_index=0
        self._step_index=0
        self._terminal_error=None

    def _record(self,row):
        p=os.environ.get('ARBM_G3_USAGE_LOG','').strip()
        if not p: raise RuntimeError('G3_USAGE_JOURNAL_REQUIRED')
        row.update({'model':self.model_id,'agent':'osworld-openrouter-free','call_index':self._call_index,
                    'step_index':self._step_index,'run_id':os.environ.get('GITHUB_RUN_ID'),
                    'run_sha':os.environ.get('GITHUB_SHA'),'zero_spend':True})
        with open(p,'a',encoding='utf-8') as f:
            f.write(json.dumps(row,separators=(',',':'))+'\n'); f.flush(); os.fsync(f.fileno())

    @staticmethod
    def _image(screenshot):
        return 'data:image/png;base64,'+base64.b64encode(screenshot).decode('ascii')
    def _messages_for(self, instruction, screenshot):
        current={'role':'user','content':[
            {'type':'text','text':'Task: '+instruction+'\nAct on the current screenshot.'},
            {'type':'image_url','image_url':{'url':self._image(screenshot)}}]}
        history=self.messages[-6:]
        return [{'role':'system','content':SYSTEM}]+history+[current]

    def _screen_gate(self, screenshot):
        digest=hashlib.sha256(screenshot).hexdigest()
        if self._last_screen is not None and digest==self._last_screen:
            self._same_screen_steps += 1
        else:
            self._same_screen_steps = 0
        self._last_screen=digest
        if self._same_screen_steps >= 4:
            self._record({'event':'blocked','reason':'SCREEN_UNCHANGED_4_STEPS'})
            raise RuntimeError('G3_NO_VISUAL_PROGRESS')

    def _call(self, instruction, screenshot):
        if self._terminal_error: raise RuntimeError(self._terminal_error)
        self._call_index += 1
        self._record({'event':'request_started','usage_status':'PENDING'})
        started=time.monotonic()
        try:
            return self.client.chat.completions.create(
                model=self.model_id,
                messages=self._messages_for(instruction,screenshot),
                tools=TOOLS, tool_choice='auto', temperature=0)
        except Exception as error:
            self._terminal_error='G3_FREE_PROVIDER_REQUEST_FAILED'
            self._record({'event':'request_failed','reason':self._terminal_error,
                          'error_type':type(error).__name__,'latency_ms':round((time.monotonic()-started)*1000,3)})
            raise RuntimeError(self._terminal_error) from None
    def _parse(self, response):
        returned=str(getattr(response,'model','') or '')
        if returned != self.model_id:
            self._record({'event':'blocked','reason':'FREE_MODEL_IDENTITY_MISMATCH','returned_model':returned})
            raise RuntimeError('G3_FREE_MODEL_IDENTITY_MISMATCH')
        choices=getattr(response,'choices',None) or []
        if not choices: raise RuntimeError('G3_FREE_NO_CHOICES')
        message=choices[0].message
        calls=message.tool_calls or []
        if len(calls) != 1:
            raise RuntimeError('G3_FREE_EXACTLY_ONE_TOOL_REQUIRED')
        call=calls[0]
        name=str(call.function.name)
        try:
            params=json.loads(call.function.arguments or '{}')
        except json.JSONDecodeError:
            raise RuntimeError('G3_FREE_TOOL_ARGUMENTS_INVALID') from None
        raw={'action_type':name,'parameters':params}
        violation=gui_action_violation(raw)
        if violation:
            self._record({'event':'action_rejected','reason':violation})
            raise RuntimeError('G3_FREE_'+violation)
        command=convert_to_pyautogui_action(raw,screen_width=1920,screen_height=1080)
        return name, params, command, str(message.content or '')

    def _record_completion(self, response):
        usage=getattr(response,'usage',None)
        prompt=int(getattr(usage,'prompt_tokens',0) or 0)
        completion=int(getattr(usage,'completion_tokens',0) or 0)
        total=int(getattr(usage,'total_tokens',prompt+completion) or prompt+completion)
        self._record({'event':'request_completed','usage_status':'RECORDED','prompt_tokens':prompt,
                      'output_tokens':completion,'total_tokens':total,'returned_model':str(response.model),
                      'reported_cost_usd':0.0,'zero_spend_contract':self.model_id.endswith(':free')})
    def predict(self, instruction, obs=None):
        if obs is None or not isinstance(obs.get('screenshot'),bytes):
            raise RuntimeError('G3_SCREENSHOT_REQUIRED')
        if not self._instruction: self._instruction=instruction
        self._step_index += 1
        screenshot=obs['screenshot']
        self._screen_gate(screenshot)
        response=self._call(self._instruction,screenshot)
        name, params, command, text=self._parse(response)
        self._record_completion(response)
        self.messages.append({'role':'user','content':'Previous GUI action executed: '+name+' '+json.dumps(params,separators=(',',':'))})
        if len(self.messages)>6: self.messages=self.messages[-6:]
        return text, [command]

    def reset(self, *args, **kwargs):
        self.messages=[]
        self._instruction=''
        self._last_screen=None
        self._same_screen_steps=0
        self._step_index=0
        self._terminal_error=None

    def reset_history(self):
        self.messages=[]
