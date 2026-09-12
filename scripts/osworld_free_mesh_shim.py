"""OpenAI-compatible OSWorld bridge. All guest execution stays in official OSWorld."""
import json, os, time, urllib.request, urllib.error, hashlib, threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from osworld_ingress import project_messages
from osworld_milestones import Milestones, verified_facts
from osworld_control import canonical_action, ground_action, Verifier, pack_payload, validate_response

UPSTREAM = 'https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v5'
EXPECTED_PIPELINE = 'arbm-osworld-v31-isolated'
EXPECTED_BUILD = 'arbm-osworld-elite-pro-v31r-20260912'
MAX_NO_PROGRESS = int(os.environ.get('ARBM_MAX_NO_PROGRESS', '12'))
MAX_WAIT_RESPONSES = int(os.environ.get('ARBM_MAX_WAIT_RESPONSES', '60'))
MAX_STEPS = int(os.environ.get('ARBM_MAX_STEPS', '160'))
LOG = os.environ.get('ARBM_OSWORLD_SHIM_LOG', 'osworld-v31-shim.log')
OBS_DIR = Path(os.environ.get('ARBM_OSWORLD_OBSERVATIONS', 'shim-observations'))
LOCK = threading.Lock()
STATE = {'step':0,'previous':'','executed':0,'phase':'plan','plan':'','memory':[],
         'history':[],'wait_responses':0,'cooldowns':{},'terminal':'','provider':'','model':''}
VERIFIER = Verifier()
MILESTONES = Milestones()
STARTED = time.monotonic()
MAX_TASK_SECONDS = int(os.environ.get('ARBM_TASK_SECONDS', '2400'))
HEALTH = {'last_event':'initializing','last_error':'','retry':0,'pending_since':None}
STOP = threading.Event()

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
    HEALTH['last_event']=data.get('status','unknown')
    if data.get('reason'):HEALTH['last_error']=data['reason']
    HEALTH['retry']=data.get('attempt',0)
    event={'timestamp':time.time(),'elapsed_seconds':round(time.monotonic()-STARTED,2),**data,'step':STATE['step'],'phase':STATE['phase'],'task_id':os.environ.get('TASK_ID'),
           'commit':os.environ.get('GITHUB_SHA'),'verifier':VERIFIER.last_result,'semantic':MILESTONES.context()}
    # No request headers/tokens or environment values are ever logged.
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
    if time.monotonic()-STARTED>=MAX_TASK_SECONDS:return terminal('TASK_DEADLINE')
    STATE['step']+=1
    obs,screenshot=latest_observation(messages)
    verification=VERIFIER.observe(obs,screenshot)
    semantic=MILESTONES.observe(obs)
    if semantic.get("status")=="VERIFIED":
        STATE["memory"].append("OBSERVED MILESTONE: "+json.dumps(semantic["milestone"],ensure_ascii=False))
        STATE["memory"]=STATE["memory"][-8:]
        log_event({"status":"MILESTONE_VERIFIED","milestone":semantic["milestone"]})
    if MILESTONES.stalled>=16:return terminal("SEMANTIC_RECOVERY_EXHAUSTED")
    if VERIFIER.no_progress>=MAX_NO_PROGRESS or STATE['wait_responses']>=MAX_WAIT_RESPONSES or STATE['step']>MAX_STEPS:
        return terminal('RECOVERY_EXHAUSTED' if STATE['step']<=MAX_STEPS else 'STEP_BUDGET')
    STATE['phase']='plan' if VERIFIER.no_progress>=2 or not STATE['plan'] else 'execute'
    body={'instruction':task_from(messages),'observation':obs,'screenshot_data_url':screenshot,
          'previous_command':STATE['previous'],'executed_count':STATE['executed'],
          'memory':'\n'.join([STATE['plan']]+STATE['memory'][-5:]+[str(x) for x in STATE['history'][-4:]]),
          'phase':STATE['phase'],'no_progress_count':VERIFIER.no_progress,'step':STATE['step'],
          'verifier':verification,'verified_milestones':MILESTONES.context(),'recovery_strategy':RECOVERY[VERIFIER.recovery_level],
          'route_cooldowns':STATE['cooldowns'],'expected_build':EXPECTED_BUILD}
    if MILESTONES.stalled>=6:body['recovery_strategy']='No verified subtask milestone. Replan from last verified fact; read required source before switching to output app. Specify a testable checkpoint.'
    if MILESTONES.stalled>=8:body['provider_hint']='text'
    elif VERIFIER.recovery_level>=4:body['provider_hint']='groq' if STATE['provider']=='mistral-free' else 'mistral'
    try:body,metrics=pack_payload(body)
    except ValueError as exc:return terminal(str(exc))
    OBS_DIR.mkdir(parents=True,exist_ok=True)
    evidence_path=OBS_DIR/('step_%04d.json'%STATE['step'])
    evidence_path.write_text(json.dumps({'request':body,'payload':metrics},ensure_ascii=False),encoding='utf-8')
    for attempt in range(3):
        if time.monotonic()-STARTED>=MAX_TASK_SECONDS-170:return terminal('TASK_DEADLINE')
        HEALTH['pending_since']=time.time()
        metrics['after_bytes']=len(json.dumps(body,ensure_ascii=False).encode())
        http,data=request_mesh(body)
        HEALTH['pending_since']=None
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
            for fact in verified_facts(action,obs):
                entry='OBSERVED SOURCE: '+json.dumps(fact,ensure_ascii=False)
                if entry not in STATE['memory']:STATE['memory'].append(entry)
            STATE['memory']=STATE['memory'][-12:]
            kind=action['action']
            STATE['provider'],STATE['model']=data.get('provider',''),data.get('model','')
            STATE['plan']=str(action.get('plan') or STATE['plan'])[:1400]
            # Model memory_patch often describes its intended next action as done.
            # Only the independently observed milestone above enters durable memory.
            if kind=='finish':
                if MILESTONES.verified and VERIFIER.can_finish(action,obs):
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
                MILESTONES.expect(action,obs)
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
    # Provider scarcity is not cognitive failure. Back off instead of burning
    # OSWorld steps rapidly while all FREE multimodal routes are cooling down.
    time.sleep(min(12, 2 + STATE['wait_responses']))
    log_event({'status':'WAIT_PROVIDER_CAPACITY','provider_waits':STATE['wait_responses'],
               'recovery_strategy':RECOVERY[VERIFIER.recovery_level]})
    return 'WAIT'

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_):pass
    def send_json(self,code,value):
        raw=json.dumps(value).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        self.send_json(200,{'status':'ok','pipeline':EXPECTED_PIPELINE,'build':EXPECTED_BUILD}) if self.path=='/health' else self.send_json(404,{})
    def do_POST(self):
        if self.path!='/v1/chat/completions':return self.send_json(404,{'error':{'code':'not_found','message':'Not found'}})
        # Close connections after every request: rejected/truncated bodies must not
        # be interpreted as another request on a keep-alive connection.
        self.close_connection=True
        self.connection.settimeout(60)
        with LOCK:
            try:
                messages,ingress=project_messages(self.rfile,int(self.headers.get('Content-Length','0')))
                log_event({'status':'INGRESS_PROJECTED','ingress':ingress})
                content=call_mesh(messages)
            except (ValueError,TimeoutError) as exc:
                content=terminal('INPUT_REJECTED:'+str(exc)[:120])
            except Exception as exc:
                # A persistent local failure terminates the agent and lets the
                # unmodified evaluator run. It can never produce DONE or PASS.
                log_event({'status':'SHIM_ERROR','error_type':type(exc).__name__,'reason':str(exc)[:200]})
                content=terminal('SHIM_INTERNAL_ERROR:'+type(exc).__name__)
        self.send_json(200,{'id':'arbm-osworld-v31-isolated','object':'chat.completion','created':int(time.time()),'model':'gpt-arbm-osworld-v31-isolated','choices':[{'index':0,'message':{'role':'assistant','content':content},'finish_reason':'stop'}],'usage':{'prompt_tokens':0,'completion_tokens':0,'total_tokens':0}})

if __name__=='__main__':
    threading.Thread(target=heartbeat,daemon=True).start()
    ThreadingHTTPServer(('127.0.0.1',8088),Handler).serve_forever()
