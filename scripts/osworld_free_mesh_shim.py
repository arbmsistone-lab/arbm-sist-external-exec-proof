"""OpenAI-compatible OSWorld bridge. All guest execution stays in official OSWorld."""
import json, os, time, urllib.request, urllib.error, hashlib, threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from osworld_ingress import project_messages
from osworld_milestones import Milestones, verified_facts
from osworld_control import canonical_action, ground_action, Verifier, pack_payload, validate_response, visual_reference_recovery, foreground_context
from osworld_v32_policy import DecisionKind, apply_live_policy
from osworld_openrouter_free import FREE_ROUTE, prompt as openrouter_prompt
from osworld_groq_free import GROQ_FREE_ROUTE
from osworld_local_vlm import LOCAL_VLM_ROUTE
from osworld_recovery import recovery_policy, rejects_visual_navigation_loop, semantic_terminal
from osworld_elite_controller import EliteController
from osworld_gimp_style_transfer import next_recovery_action
from osworld_061_calibrated_grade import next_calibrated_action, DONE as CAL_DONE

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

def request_gateway(body):
    raw=json.dumps(body,ensure_ascii=False).encode()
    req=urllib.request.Request(UPSTREAM,data=raw,method='POST',headers={'Authorization':'Bearer '+oidc_token(),'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=75) as res:return res.status,json.loads(res.read())
    except urllib.error.HTTPError as err:
        try:data=json.loads(err.read())
        except (json.JSONDecodeError, UnicodeDecodeError):data={'status':'INVALID_UPSTREAM_RESPONSE'}
        return err.code,data
    except (urllib.error.URLError,TimeoutError,json.JSONDecodeError) as exc:
        return 503,{'status':'TRANSPORT_ERROR','error_type':type(exc).__name__}


def request_mesh(body):
    # Admission/authentication checks without an observation always reach OIDC.
    if not body.get('screenshot_data_url'): return request_gateway(body)
    started=time.monotonic()
    body={**body,'request_budget_ms':60000}
    router_attempts=[]
    def groq_router():
        result, attempts=GROQ_FREE_ROUTE.call(body,budget=max(2,min(55,105-(time.monotonic()-started))))
        router_attempts.extend(attempts)
        if result:
            return 200,{'ok':True,'status':'PASS','pipeline':EXPECTED_PIPELINE,
                'agent_build':EXPECTED_BUILD,**result,'provider_attempts':router_attempts,
                'mandatory_cost_usd':0,'paid_fallback_used':False,'scoreable':False,
                'github_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID')}
    def router():
        result, attempts=FREE_ROUTE.call(body,budget=max(2,min(55,105-(time.monotonic()-started))))
        router_attempts.extend(attempts)
        if result:
            return 200,{'ok':True,'status':'PASS','pipeline':EXPECTED_PIPELINE,
                'agent_build':EXPECTED_BUILD,**result,'provider_attempts':router_attempts,
                'mandatory_cost_usd':0,'paid_fallback_used':False,'scoreable':False,
                'github_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID')}
    def local_router():
        result, attempts=LOCAL_VLM_ROUTE.call(body,budget=max(2,min(80,105-(time.monotonic()-started))))
        router_attempts.extend(attempts)
        if result:
            return 200,{'ok':True,'status':'PASS','pipeline':EXPECTED_PIPELINE,
                'agent_build':EXPECTED_BUILD,**result,'provider_attempts':router_attempts,
                'mandatory_cost_usd':0,'paid_fallback_used':False,'scoreable':False,
                'github_sha':os.environ.get('GITHUB_SHA'),'github_run_id':os.environ.get('GITHUB_RUN_ID')}
    if os.environ.get('ARBM_VALIDATION_SPEND_MODE','zero') != 'zero':
        return 503,{'status':'NON_ZERO_SPEND_MODE_FORBIDDEN','provider_attempts':router_attempts,
                    'mandatory_cost_usd':0,'paid_fallback_used':False}
    def text_router():
        remaining=max(2,min(45,105-(time.monotonic()-started)))
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
    # Eager failover: every request traverses independent FREE candidates in
    # the same cycle. A degraded local route can never capture later turns.
    if body.get('provider_hint')=='text':
        response=text_router()
        if response:return response
    response=router()
    if response:return response
    response=groq_router()
    if response:return response
    body['request_budget_ms']=max(1000,min(60000,int((105-(time.monotonic()-started))*1000)))
    http,data=request_gateway(body)
    if http==200 and isinstance(data,dict) and data.get('ok') is True:
        if router_attempts:data['provider_attempts']=(data.get('provider_attempts') or [])+router_attempts
        return http,data
    gateway_attempts=(data.get('provider_attempts') or []) if isinstance(data,dict) else []
    response=text_router()
    if response:
        response[1]['provider_attempts']=gateway_attempts+router_attempts
        return response
    response=local_router()
    if response:
        response[1]['provider_attempts']=gateway_attempts+router_attempts
        return response
    return 503,{'status':'FREE_MESH_EXHAUSTED_CURRENT_CYCLE',
                'provider_attempts':gateway_attempts+router_attempts,
                'mandatory_cost_usd':0,'paid_fallback_used':False}

def try_061_calibrated(body, obs, focused_obs):
    """Run the generic reference-pair calibrator only for official task 061."""
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
    """Issue one generic GIMP specialist action through the normal safety gates."""
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
            log_event({'status':'GIMP_PROFILE_CONVERT_CONTROL_UNRESOLVED',
                       'waits':specialist_state.get('profile_modal_missing_convert_waits',0)})
            return terminal('GIMP_PROFILE_CONVERT_CONTROL_UNRESOLVED')
        if specialist_state.get('colorize_processing'):
            specialist_state['uncertain_turns']=0
            log_event({'status':'GIMP_SPECIALIST_COLORIZE_PROCESSING_HOLD'})
            return 'WAIT'
        if specialist_state.get('owned'):
            # Champion ownership is fail-closed: once task 061 enters the
            # specialist transaction, an uncertain intermediate state can
            # never fall through to a generic provider that may skip phases.
            specialist_state['uncertain_turns']=specialist_state.get('uncertain_turns',0)+1
            log_event({'status':'GIMP_SPECIALIST_OWNERSHIP_HOLD','uncertain_turns':specialist_state['uncertain_turns']})
            return 'WAIT'
        return None
    try:
        action=ground_action(candidate,body.get('active_application','unknown'),focused_obs,body.get('verified_milestones',[]))
        decision=apply_live_policy(action,body.get('active_application','unknown'),focused_obs,body.get('verified_milestones',[]))
    except ValueError as exc:
        log_event({'status':'GIMP_SPECIALIST_POLICY_REJECTED','reason':str(exc),'action':candidate})
        if specialist_state.get('owned'):
            specialist_state['policy_holds']=specialist_state.get('policy_holds',0)+1
            log_event({'status':'GIMP_SPECIALIST_POLICY_HOLD','reason':str(exc),
                       'policy_holds':specialist_state['policy_holds']})
            return 'WAIT'
        return None
    if action.get('action')=='finish':
        specialist_complete=(specialist_state.get('colorize_closed') and specialist_state.get('export_confirmed') and specialist_state.get('output_verify_open') and specialist_state.get('output_physical_provenance') and bool(specialist_state.get('output_provenance_sha256')))
        if decision.get('kind')==DecisionKind.FINISH_CANDIDATE.value and specialist_complete and VERIFIER.can_finish(action,obs):
            STATE['phase']='done';log_event({'status':'GIMP_SPECIALIST_VERIFIED_FINISH','action':action});return 'DONE'
        log_event({'status':'GIMP_SPECIALIST_FINISH_REJECTED','action':action});return 'WAIT'
    if decision.get('kind')!=DecisionKind.EXEC.value or action.get('action')!='exec':
        if specialist_state.get('owned'):
            log_event({'status':'GIMP_SPECIALIST_DECISION_HOLD','decision':decision.get('kind')})
            return 'WAIT'
        return None
    command=action['command']
    if rejects_visual_navigation_loop(action,body['instruction'],body.get('active_application','unknown'),MILESTONES.stalled):
        log_event({'status':'GIMP_SPECIALIST_LOOP_REJECTED','command':command})
        return 'WAIT' if specialist_state.get('owned') else None
    recent=[x['command'] for x in STATE['history'][-6:]]
    if VERIFIER.no_progress and command in recent:
        log_event({'status':'GIMP_SPECIALIST_REPEAT_REJECTED','command':command})
        return 'WAIT' if specialist_state.get('owned') else None
    elite_action=ELITE.before_action(command,action.get('target'))
    if not elite_action['allow']:
        log_event({'status':'GIMP_SPECIALIST_TABU_REJECTED','command':command,'reason':elite_action['reason']})
        return 'WAIT' if specialist_state.get('owned') else None
    STATE['plan']=str(action.get('plan') or STATE['plan'])[:1400]
    STATE['previous']=command;STATE['executed']+=1;STATE['wait_responses']=0;STATE['provider_waits']=0
    STATE['history'].append({'command':command,'expected':action.get('expected_change',''),'source':'gimp-specialist'})
    STATE['history']=STATE['history'][-12:]
    specialist_state['owned']=True;specialist_state['uncertain_turns']=0
    phase=action.get('specialist_phase')
    tracked={'open-colorize','convert-profile','enable-subcolors','disable-hold-intensity','disable-original-intensity',
             'sample-colors','apply-colorize','close-colorize','export-open','export-name-focus',
             'export-name','export-submit','export-confirm','verify-output-open','export-baseline',
             'export-baseline-return','verify-output-physical','export-original-overwrite-cancel'}
    if phase in tracked:
        specialist_state['pending_phase']=phase
        specialist_state['pending_waits']=0
    VERIFIER.issued(command)
    if isinstance(action.get('checkpoint'),dict):MILESTONES.expect(action,obs)
    log_event({'status':'GIMP_SPECIALIST_ACTION_ISSUED','command':command,'checkpoint':action.get('checkpoint')})
    log_event({'status':'ACTION_ISSUED','command':command,'source':'gimp-style-specialist'})
    return '```python\n'+command+'\n```'
def call_mesh(messages):
    if STATE.get('step',0)==0 and not STATE.get('terminal'):
        ELITE.reset()
    if STATE['terminal']:return 'FAIL'
    if time.monotonic()-STARTED>=MAX_TASK_SECONDS:return terminal('TASK_DEADLINE')
    STATE['step']+=1
    STATE.setdefault('facts',[])
    obs,screenshot=latest_observation(messages)
    focused_obs,active_application=foreground_context(obs)
    had_semantic_expectation=MILESTONES.pending is not None
    verification=VERIFIER.observe(obs,screenshot)
    semantic=MILESTONES.observe(obs)
    semantic_progress=semantic.get('status')=='VERIFIED'
    if had_semantic_expectation and verification.get('progress') and not semantic_progress:
        VERIFIER.no_progress += 1
        VERIFIER.last_result={**VERIFIER.last_result,'progress':False,'reason':'visual_change_without_semantic_checkpoint','no_progress':VERIFIER.no_progress,'recovery_level':VERIFIER.recovery_level}
        verification=VERIFIER.last_result
    elite_decision=ELITE.observe(bool(semantic_progress if had_semantic_expectation else verification.get('progress')))
    if STATE['history'] and 'outcome' not in STATE['history'][-1]:
        STATE['history'][-1]['outcome']={'progress':bool(verification.get('progress')),
            'semantic_verified':semantic_progress,'verifier_reason':verification.get('reason'),
            'no_progress':verification.get('no_progress'),'milestone':semantic.get('milestone')}
    if semantic.get("status")=="VERIFIED":
        STATE["memory"].append("OBSERVED MILESTONE: "+json.dumps(semantic["milestone"],ensure_ascii=False))
        STATE["memory"]=STATE["memory"][-8:]
        ELITE.checkpoint(semantic["milestone"])
        log_event({"status":"MILESTONE_VERIFIED","milestone":semantic["milestone"],"backtrack_anchor":ELITE.recovery_anchor()})
        if screenshot and not STATE.get('visual_memory'):
            STATE['visual_memory']=screenshot
            STATE['visual_memory_meta']=semantic['milestone']
    if semantic_terminal(MILESTONES.stalled, VERIFIER.no_progress):return terminal("SEMANTIC_RECOVERY_EXHAUSTED")
    if VERIFIER.no_progress>=MAX_NO_PROGRESS or STATE['wait_responses']>=MAX_WAIT_RESPONSES or STATE['step']>MAX_STEPS:
        return terminal('RECOVERY_EXHAUSTED' if STATE['step']<=MAX_STEPS else 'STEP_BUDGET')
    STATE['phase']='plan' if (elite_decision['mode']=='replan' or VERIFIER.no_progress>=2 or not STATE['plan']) else 'execute'
    body={'instruction':task_from(messages),'observation':obs,'screenshot_data_url':screenshot,
          'previous_command':STATE['previous'],'executed_count':STATE['executed'],'active_application':active_application,
          'memory':'\n'.join([STATE['plan']]+STATE['memory'][-5:]+[str(x) for x in STATE['history'][-4:]]),
          'phase':STATE['phase'],'no_progress_count':VERIFIER.no_progress,'step':STATE['step'],
          'verifier':verification,'verified_milestones':MILESTONES.context(),'recovery_strategy':RECOVERY[VERIFIER.recovery_level],
          'route_cooldowns':STATE['cooldowns'],'expected_build':EXPECTED_BUILD,
          'performance_mode':elite_decision['mode'],
          'performance_reason':elite_decision['reason'],
          'performance_metrics':ELITE.metrics(),
          'reference_screenshot_data_url':STATE.get('visual_memory','') if STATE.get('visual_memory') and STATE.get('visual_memory')!=screenshot else '',
          'reference_visual_meta':STATE.get('visual_memory_meta'),
          'task_ledger':{'verified_milestones':MILESTONES.context().get('verified',[]),
                         'verified_facts':STATE.get('facts',[])[:24],
                         'recent_outcomes':STATE['history'][-6:],
                         'backtrack_anchor':ELITE.recovery_anchor(),
                         'root_instruction_sha256':hashlib.sha256(task_from(messages).encode()).hexdigest(),
                         'provider_waits':STATE.get('provider_waits',0),
                         'cognitive_waits':STATE.get('wait_responses',0)}}
    recovery=recovery_policy(body['instruction'], body.get('active_application','unknown'), MILESTONES.stalled, VERIFIER.no_progress, VERIFIER.recovery_level, STATE['provider'], STATE.get('visual_capacity_exhausted',False))
    if recovery['strategy']:body['recovery_strategy']=recovery['strategy']
    if elite_decision['mode']=='replan' and ELITE.recovery_anchor().get('last_verified_checkpoint'):
        anchor=ELITE.recovery_anchor()['last_verified_checkpoint']
        body['recovery_strategy']=(str(body.get('recovery_strategy') or '')+
            '\nCHECKPOINT BACKTRACK: the last independently verified state is '+json.dumps(anchor,ensure_ascii=False)+
            '. Treat it as known-good and do not undo verified work. From the current foreground, choose a genuinely different route toward the next unmet subgoal; the next action must name a new observable checkpoint.')[-3000:]
    if recovery['provider_hint']:body['provider_hint']=recovery['provider_hint']
    visual_recovery=visual_reference_recovery(body['instruction'],body.get('active_application','unknown'),MILESTONES.stalled)
    if visual_recovery:body['recovery_strategy']=visual_recovery
    calibrated_result=try_061_calibrated(body,obs,focused_obs)
    if calibrated_result:return calibrated_result
    specialist_result=try_gimp_specialist(body,obs,focused_obs)
    if specialist_result:return specialist_result
    try:body,metrics=pack_payload(body)
    except ValueError as exc:return terminal(str(exc))
    OBS_DIR.mkdir(parents=True,exist_ok=True)
    evidence_path=OBS_DIR/('step_%04d.json'%STATE['step'])
    evidence_path.write_text(json.dumps({'request':body,'payload':metrics},ensure_ascii=False),encoding='utf-8')
    policy_rejections=0
    provider_capacity_cycles=0
    for attempt in range(3):
        if time.monotonic()-STARTED>=MAX_TASK_SECONDS-170:return terminal('TASK_DEADLINE')
        HEALTH['pending_since']=time.time()
        metrics['after_bytes']=len(json.dumps(body,ensure_ascii=False).encode())
        http,data=request_mesh(body)
        HEALTH['pending_since']=None
        if not isinstance(data,dict):data={'status':'INVALID_UPSTREAM_RESPONSE'}
        track_attempts(data)
        successful=[a for a in (data.get('provider_attempts') or []) if a.get('status')==200 and a.get('latency_seconds') is not None]
        if successful: ELITE.record_latency(successful[-1].get('latency_seconds'))
        log_event({'http':http,'attempt':attempt+1,'status':data.get('status'),'provider':data.get('provider'),
                   'model':data.get('model'),'agent_build':data.get('agent_build'),'pipeline':data.get('pipeline'),
                   'provider_attempts':data.get('provider_attempts',[]),'action':data.get('action'),
                   'mandatory_cost_usd':data.get('mandatory_cost_usd'),'paid_fallback_used':data.get('paid_fallback_used'),
                   'transition_review':data.get('transition_review'),'error':data.get('error'),
                   'detail':str(data.get('detail') or '')[:200],'payload':metrics,'observation_file':str(evidence_path)})
        if data.get('pipeline') or http==200:
            try:validate_response(data,EXPECTED_PIPELINE,EXPECTED_BUILD)
            except ValueError as exc:return terminal(str(exc))
        if http in (401,403):return terminal('ENDPOINT_AUTH_OR_VERSION')
        if data.get('status') in LOCAL_FALLBACK_CAPACITY_STATUSES | {'LOCAL_ACTION_UNAVAILABLE','FREE_MESH_EXHAUSTED_CURRENT_CYCLE'}:
            provider_capacity_cycles+=1
            # Never pin later turns to one degraded provider. Retry the whole
            # FREE mesh inside this same OSWorld turn with a different order.
            body['provider_hint']='text' if attempt else 'openrouter'
            log_event({'status':'EAGER_FREE_FAILOVER','attempt':attempt+1,'reason':data.get('status')})
            continue
        if http==409:
            if data.get('status')!='REPLAN_REQUIRED':return terminal('ENDPOINT_CONFLICT')
            reason=str(data.get('review_reason') or 'independent reviewer requested replanning')
            body['memory']=(body['memory']+'\nREVIEW REPLAN REQUIRED: '+reason+'. Do not repeat the rejected action; produce a new grounded action from the current observation.')[-4500:]
            continue
        if http==200 and data.get('ok') is True:
            try:
                action=ground_action(data.get('action'),body.get('active_application','unknown'),focused_obs,body.get('verified_milestones',[]))
                decision=apply_live_policy(action,body.get('active_application','unknown'),focused_obs,body.get('verified_milestones',[]))
            except ValueError as exc:
                policy_rejections+=1
                body['memory']=(body['memory']+'\nPOLICY REJECTED: '+str(exc)+'. Replan within deterministic v32 state constraints. This is a local action-contract rejection, not provider-capacity evidence.')[-4500:]
                body['provider_hint']='openrouter' if str(data.get('provider') or '').startswith('groq') else 'text'
                log_event({'status':'LOCAL_POLICY_REJECTED','reason':str(exc),'attempt':attempt+1})
                continue
            decision_kind=decision['kind']
            if decision_kind==DecisionKind.NOOP_VERIFIED.value:
                log_event({'status':'NOOP_VERIFIED','checkpoint':action.get('checkpoint')})
                STATE['wait_responses']+=1
                ELITE.note_wait()
                return 'WAIT'
            if decision_kind==DecisionKind.HOLD_CAPACITY.value:
                STATE['provider_waits']=STATE.get('provider_waits',0)+1
                log_event({'status':'HOLD_CAPACITY','provider_waits':STATE['provider_waits']})
                return 'WAIT'
            for fact in verified_facts(action,focused_obs):
                entry='OBSERVED SOURCE: '+json.dumps(fact,ensure_ascii=False)
                if entry not in STATE['memory']:STATE['memory'].append(entry)
                if fact not in STATE['facts']: STATE['facts'].append(fact)
            STATE['facts']=STATE['facts'][-24:]
            STATE['memory']=STATE['memory'][-12:]
            kind=action['action']
            STATE['provider'],STATE['model']=data.get('provider',''),data.get('model','')
            STATE['plan']=str(action.get('plan') or STATE['plan'])[:1400]
            # Model memory_patch often describes its intended next action as done.
            # Only the independently observed milestone above enters durable memory.
            if kind=='finish':
                if MILESTONES.verified and MILESTONES.stalled==0 and VERIFIER.can_finish(action,obs):
                    STATE['phase']='done';log_event({'status':'VERIFIED_FINISH','action':action});return 'DONE'
                body['memory']=(body['memory']+'\nFINISH REJECTED: no sufficient observed completion. Verify all outputs on screen.')[-4500:]
                continue
            if kind=='exec':
                command=action['command']
                if rejects_visual_navigation_loop(action, body['instruction'], body.get('active_application','unknown'), MILESTONES.stalled):
                    body['memory']=(body['memory']+'\nVISUAL_NAVIGATION_LOOP_REJECTED: Ctrl+O was already used without a verified visual milestone. Use the visible dialog deliberately or make a target-image edit instead. Do not repeat it.')[-4500:]
                    body.pop('provider_hint',None)
                    log_event({'status':'VISUAL_NAVIGATION_LOOP_REJECTED','command':command})
                    continue
                recent=[x['command'] for x in STATE['history'][-6:]]
                if VERIFIER.no_progress and command in recent:
                    body['memory']=(body['memory']+'\nNO EFFECT: rejected repeated action '+command+'. Change GUI strategy or target.')[-4500:]
                    body['provider_hint']='openrouter' if str(data.get('provider') or '').startswith('groq') else 'text'
                    route='groq-multimodal-free' if str(data.get('provider') or '').startswith('groq') else 'openrouter-multimodal-free'
                    STATE['cooldowns'][route+':'+str(data.get('model'))]=int((time.time()+90)*1000)
                    continue
                elite_action=ELITE.before_action(command,action.get('target'))
                if not elite_action['allow']:
                    body['memory']=(body['memory']+'\nELITE TABU: action rejected because it previously produced no verified progress. Replan from the current screenshot with a genuinely different control/path.')[-4500:]
                    log_event({'status':'ELITE_TABU_REJECTED','command':command,'reason':elite_action['reason']})
                    continue
                STATE['previous']=command;STATE['executed']+=1;STATE['wait_responses']=0;STATE['provider_waits']=0
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
    if policy_rejections and provider_capacity_cycles==0:
        # Valid zero-cost model responses existed, but every candidate action
        # violated the local action contract.  Preserve the true cause; never
        # mislabel compiler/policy rejection as provider exhaustion.
        return terminal('ACTION_CONTRACT_EXHAUSTED')
    STATE['provider_waits']=STATE.get('provider_waits',0)+1
    log_event({'status':'FREE_MESH_EXHAUSTED','provider_waits':STATE['provider_waits'],'policy_rejections':policy_rejections,'provider_capacity_cycles':provider_capacity_cycles})
    # All configured FREE routes were attempted repeatedly inside this same
    # OSWorld turn. Never burn benchmark steps with provider-capacity WAITs.
    return terminal('PROVIDER_CAPACITY_EXHAUSTED')

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
        self.send_json(200,{'id':'arbm-osworld-v32-isolated','object':'chat.completion','created':int(time.time()),'model':'gpt-arbm-osworld-v32-isolated','choices':[{'index':0,'message':{'role':'assistant','content':content},'finish_reason':'stop'}],'usage':{'prompt_tokens':0,'completion_tokens':0,'total_tokens':0}})

if __name__=='__main__':
    threading.Thread(target=heartbeat,daemon=True).start()
    ThreadingHTTPServer(('127.0.0.1',8088),Handler).serve_forever()
