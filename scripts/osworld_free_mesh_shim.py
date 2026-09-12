"""OpenAI-compatible OSWorld bridge. All guest execution stays in official OSWorld."""
import json, os, time, urllib.request, urllib.error, hashlib, threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from osworld_control import canonical_action, ground_action, Verifier, pack_payload, validate_response

UPSTREAM = 'https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v5'
EXPECTED_PIPELINE = 'arbm-osworld-v31-isolated'
EXPECTED_BUILD = 'arbm-osworld-v31o-isolated-20260912'
MAX_NO_PROGRESS = int(os.environ.get('ARBM_MAX_NO_PROGRESS', '12'))
MAX_WAIT_RESPONSES = int(os.environ.get('ARBM_MAX_WAIT_RESPONSES', '12'))
MAX_STEPS = int(os.environ.get('ARBM_MAX_STEPS', '160'))
LOG = os.environ.get('ARBM_OSWORLD_SHIM_LOG', 'osworld-v31-shim.log')
OBS_DIR = Path(os.environ.get('ARBM_OSWORLD_OBSERVATIONS', 'shim-observations'))
LOCK = threading.Lock()
STATE = {'step':0,'previous':'','executed':0,'phase':'plan','plan':'','memory':[],
         'history':[],'wait_responses':0,'cooldowns':{},'terminal':'','provider':'','model':''}
VERIFIER = Verifier()

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
    req=urllib.request.Request(url+('&' if '?' in url else '?')+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+token})
    with urllib.request.urlopen(req,timeout=20) as res:return json.loads(res.read())['value']

def task_from(messages):
    import re
    system='\n'.join(content_parts(m.get('content'))[0] for m in messages if m.get('role')=='system')
    match=re.search(r'You are asked to complete the following task:\s*(.*)$',system,re.S)
    return match.group(1).strip() if match else system[-7000:]

def latest_observation(messages):
    users=[m for m in messages if m.get('role')=='user']
    if not users:return '', ''
    text,images=content_parts(users[-1].get('content'))
    return text,images[-1] if images else ''

def log_event(data):
    event={**data,'step':STATE['step'],'phase':STATE['phase'],'task_id':os.environ.get('TASK_ID'),
           'commit':os.environ.get('GITHUB_SHA'),'verifier':VERIFIER.last_result}
    # No request headers/tokens or environment values are ever logged.
    with open(LOG,'a',encoding='utf-8') as f:f.write(json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n')

def terminal(reason):
    STATE['terminal']=reason
    log_event({'status':'TERMINAL_FAIL','reason':reason,'agent_build':EXPECTED_BUILD})
    return 'FAIL'

def track_attempts(data):
    for a in data.get('provider_attempts') or []:
        key=str(a.get('route'))+':'+str(a.get('model'))
        status=a.get('status')
        seconds=0
        if status==200 and a.get('route')=='groq-multimodal-free':
            seconds=max(25,min(65,float(a.get('prompt_tokens') or 4500)/7000*60+3))
        elif status==413:seconds=3600
        elif status in (401,403,404):seconds=3600
        elif status==429:
            try:seconds=max(65,min(3600,float(a.get('retry_after') or 65)))
            except (ValueError,TypeError):seconds=65
        elif isinstance(status,int) and status>=500:seconds=30
        elif a.get('contract_error'):seconds=90
        if seconds:STATE['cooldowns'][key]=int((time.time()+seconds)*1000)

def request_mesh(body):
    raw=json.dumps(body,ensure_ascii=False).encode()
    req=urllib.request.Request(UPSTREAM,data=raw,method='POST',headers={'Authorization':'Bearer '+oidc_token(),'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=165) as res:return res.status,json.loads(res.read())
    except urllib.error.HTTPError as err:
        try:data=json.loads(err.read())
        except Exception:data={'status':'INVALID_UPSTREAM_RESPONSE'}
        return err.code,data
    except (urllib.error.URLError,TimeoutError,json.JSONDecodeError) as exc:
        return 503,{'status':'TRANSPORT_ERROR','error_type':type(exc).__name__}

def call_mesh(messages):
    if STATE['terminal']:return 'FAIL'
    STATE['step']+=1
    obs,screenshot=latest_observation(messages)
    verification=VERIFIER.observe(obs,screenshot)
    if VERIFIER.no_progress>=MAX_NO_PROGRESS or STATE['wait_responses']>=MAX_WAIT_RESPONSES or STATE['step']>MAX_STEPS:
        return terminal('RECOVERY_EXHAUSTED' if STATE['step']<=MAX_STEPS else 'STEP_BUDGET')
    STATE['phase']='plan' if VERIFIER.no_progress>=2 or not STATE['plan'] else 'execute'
    body={'instruction':task_from(messages),'observation':obs,'screenshot_data_url':screenshot,
          'previous_command':STATE['previous'],'executed_count':STATE['executed'],
          'memory':'\n'.join([STATE['plan']]+STATE['memory'][-5:]+[str(x) for x in STATE['history'][-4:]]),
          'phase':STATE['phase'],'no_progress_count':VERIFIER.no_progress,'step':STATE['step'],
          'verifier':verification,'recovery_strategy':RECOVERY[VERIFIER.recovery_level],
          'route_cooldowns':STATE['cooldowns'],'expected_build':EXPECTED_BUILD}
    if VERIFIER.recovery_level>=4:body['provider_hint']='groq' if STATE['provider']=='mistral-free' else 'mistral'
    try:body,metrics=pack_payload(body)
    except ValueError as exc:return terminal(str(exc))
    OBS_DIR.mkdir(parents=True,exist_ok=True)
    evidence_path=OBS_DIR/('step_%04d.json'%STATE['step'])
    evidence_path.write_text(json.dumps({'request':body,'payload':metrics},ensure_ascii=False),encoding='utf-8')
    for attempt in range(3):
        metrics['after_bytes']=len(json.dumps(body,ensure_ascii=False).encode())
        http,data=request_mesh(body)
        if not isinstance(data,dict):data={'status':'INVALID_UPSTREAM_RESPONSE'}
        track_attempts(data)
        log_event({'http':http,'attempt':attempt+1,'status':data.get('status'),'provider':data.get('provider'),
                   'model':data.get('model'),'agent_build':data.get('agent_build'),'pipeline':data.get('pipeline'),
                   'provider_attempts':data.get('provider_attempts',[]),'action':data.get('action'),
                   'mandatory_cost_usd':data.get('mandatory_cost_usd'),'paid_fallback_used':data.get('paid_fallback_used'),
                   'payload':metrics,'observation_file':str(evidence_path)})
        if data.get('pipeline') or http==200:
            try:validate_response(data,EXPECTED_PIPELINE,EXPECTED_BUILD)
            except ValueError as exc:return terminal(str(exc))
        if http in (401,403,409):return terminal('ENDPOINT_AUTH_OR_VERSION')
        if http==200 and data.get('ok') is True:
            try:action=ground_action(data.get('action'),body.get('active_application','unknown'))
            except ValueError as exc:
                body['memory']=(body['memory']+'\nCONTRACT REJECTED: '+str(exc)+'. Return literal pyautogui call strings only.')[-4500:]
                body['provider_hint']='groq' if data.get('provider')=='mistral-free' else 'mistral'
                continue
            kind=action['action']
            STATE['provider'],STATE['model']=data.get('provider',''),data.get('model','')
            STATE['plan']=str(action.get('plan') or STATE['plan'])[:1400]
            if action.get('memory_patch'):STATE['memory'].append(str(action['memory_patch'])[:1600])
            STATE['memory']=STATE['memory'][-8:]
            if kind=='finish':
                if VERIFIER.can_finish(action,obs):
                    STATE['phase']='done';log_event({'status':'VERIFIED_FINISH','action':action});return 'DONE'
                body['memory']=(body['memory']+'\nFINISH REJECTED: no sufficient observed completion. Verify all outputs on screen.')[-4500:]
                continue
            if kind=='exec':
                command=action['command']
                recent=[x['command'] for x in STATE['history'][-6:]]
                if VERIFIER.no_progress and command in recent:
                    body['memory']=(body['memory']+'\nNO EFFECT: rejected repeated action '+command+'. Change GUI strategy or target.')[-4500:]
                    body['provider_hint']='groq' if data.get('provider')=='mistral-free' else 'mistral'
                    route='mistral-multimodal-free' if data.get('provider')=='mistral-free' else 'groq-multimodal-free'
                    STATE['cooldowns'][route+':'+str(data.get('model'))]=int((time.time()+90)*1000)
                    continue
                STATE['previous']=command;STATE['executed']+=1;STATE['wait_responses']=0
                STATE['history'].append({'command':command,'expected':action.get('expected_change','')})
                STATE['history']=STATE['history'][-12:]
                VERIFIER.issued(command)
                log_event({'status':'ACTION_ISSUED','command':command})
                return '```python\n'+command+'\n```'
            break
        if http==413:
            # Shrink useful text once; persistent route cooldown prevents repeated provider 413s.
            body['observation']=body['observation'][:4000];body['memory']=body['memory'][-1500:]
        elif http==422:
            body['memory']=(body['memory']+'\nRecover invalid action: exec/finish/wait only. Command must be a valid literal Python string.')[-4500:]
        elif http in (429,500,502,503,504):
            body['route_cooldowns']=STATE['cooldowns']
            time.sleep(2+attempt)
        else:break
    STATE['wait_responses']+=1
    log_event({'status':'WAIT_RECOVERY','recovery_strategy':RECOVERY[VERIFIER.recovery_level]})
    return 'WAIT'

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def send_json(self,code,value):
        raw=json.dumps(value).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        self.send_json(200,{'status':'ok','pipeline':EXPECTED_PIPELINE,'build':EXPECTED_BUILD}) if self.path=='/health' else self.send_json(404,{})
    def do_POST(self):
        if self.path!='/v1/chat/completions':return self.send_json(404,{'error':{'code':'not_found','message':'Not found'}})
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n>32_000_000:raise ValueError('INPUT_PAYLOAD_GATE')
            body=json.loads(self.rfile.read(n) or b'{}')
            with LOCK:content=call_mesh(body.get('messages') or [])
            self.send_json(200,{'id':'arbm-osworld-v31-isolated','object':'chat.completion','created':int(time.time()),'model':'gpt-arbm-osworld-v31-isolated','choices':[{'index':0,'message':{'role':'assistant','content':content},'finish_reason':'stop'}],'usage':{'prompt_tokens':0,'completion_tokens':0,'total_tokens':0}})
        except Exception as exc:
            log_event({'status':'SHIM_ERROR','error_type':type(exc).__name__})
            self.send_json(500,{'error':{'message':str(exc)[:200],'type':'server_error','param':None,'code':'shim_internal_error'}})

if __name__=='__main__':
    ThreadingHTTPServer(('127.0.0.1',8088),Handler).serve_forever()
