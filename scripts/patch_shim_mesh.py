#!/usr/bin/env python3
"""Apply the ARBM mesh hotfix deterministically to a fresh CI worktree.

The source branch stays reviewable: this patcher is idempotent, fail-closed and
only touches the two explicitly audited runtime files.  CI executes it before
all isolated/full OSWorld runs until the hotfix is promoted into the sources.
"""
from pathlib import Path
import hashlib

SHIM = Path('scripts/osworld_free_mesh_shim.py')
LOCAL = Path('scripts/osworld_local_vlm.py')
MARKER = 'ARBM_SHIM_MESH_BUDGET_SESSION_V1'
LOCAL_MARKER = 'ARBM_LOCAL_VLM_PARSE_RECOVERY_V1'


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'PATCH_CONTEXT_{label}_COUNT={count}')
    return text.replace(old, new, 1)


def patch_shim(text: str) -> str:
    if MARKER in text:
        return text

    text = replace_once(
        text,
        'import json, os, time, urllib.request, urllib.error, hashlib, threading',
        'import argparse, json, os, time, urllib.request, urllib.error, hashlib, threading',
        'IMPORT',
    )

    anchor = "STOP = threading.Event()\n"
    insertion = r'''

# ARBM_SHIM_MESH_BUDGET_SESSION_V1
MESH_TOTAL_BUDGET_SECONDS = float(os.environ.get('ARBM_MESH_TOTAL_BUDGET_SECONDS', '105'))
LOCAL_VLM_RESERVE_SECONDS = float(os.environ.get('ARBM_LOCAL_VLM_RESERVE_SECONDS', '25'))
GATEWAY_TIMEOUT_CAP_SECONDS = float(os.environ.get('ARBM_GATEWAY_TIMEOUT_CAP_SECONDS', '45'))
MAX_SESSION_STORES = int(os.environ.get('ARBM_MAX_SESSION_STORES', '32'))
SESSION_STORES = {}
CURRENT_SESSION_KEY = 'bootstrap'


def _new_state():
    return {'step':0,'previous':'','executed':0,'phase':'plan','plan':'','memory':[],
            'history':[],'facts':[],'wait_responses':0,'provider_waits':0,'cooldowns':{},
            'terminal':'','provider':'','model':'','visual_memory':'','visual_memory_meta':None,
            'gimp_specialist':{}}


def _new_elite():
    return EliteController(
        fast_latency_s=float(os.environ.get('ARBM_ELITE_FAST_LATENCY_S','8')),
        hard_latency_s=float(os.environ.get('ARBM_ELITE_HARD_LATENCY_S','20')),
        max_waits=int(os.environ.get('ARBM_ELITE_MAX_WAITS','2')),
        max_stall=int(os.environ.get('ARBM_ELITE_MAX_STALL','3')))


def _new_session_bundle():
    return {
        'state': _new_state(),
        'verifier': Verifier(),
        'milestones': Milestones(),
        'elite': _new_elite(),
        'health': {'last_event':'initializing','last_error':'','retry':0,'pending_since':None},
        'started': time.monotonic(),
        'last_used': time.time(),
    }


def _session_key(raw=''):
    raw = str(raw or (os.environ.get('GITHUB_RUN_ID','local') + ':' + os.environ.get('TASK_ID','unknown')))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]


def activate_session(raw_key=''):
    """Swap all mutable runtime state to a stable per-run/task bundle.

    Handler still holds the existing global LOCK while a bundle is active, so
    no two sessions can mutate the module globals concurrently.  The registry
    prevents sequential requests from different sessions sharing state.
    """
    global STATE, VERIFIER, MILESTONES, ELITE, HEALTH, STARTED, CURRENT_SESSION_KEY
    key = _session_key(raw_key)
    bundle = SESSION_STORES.get(key)
    if bundle is None:
        if len(SESSION_STORES) >= MAX_SESSION_STORES:
            oldest = min(SESSION_STORES, key=lambda item: SESSION_STORES[item]['last_used'])
            SESSION_STORES.pop(oldest, None)
        bundle = _new_session_bundle()
        SESSION_STORES[key] = bundle
    bundle['last_used'] = time.time()
    STATE = bundle['state']
    VERIFIER = bundle['verifier']
    MILESTONES = bundle['milestones']
    ELITE = bundle['elite']
    HEALTH = bundle['health']
    STARTED = bundle['started']
    CURRENT_SESSION_KEY = key
    return key


def mesh_remaining(started):
    return max(0.0, MESH_TOTAL_BUDGET_SECONDS - (time.monotonic() - started))


def mesh_external_budget(started, cap):
    # External routes are never allowed to consume the local VLM reserve.
    return max(2.0, min(float(cap), max(0.0, mesh_remaining(started) - LOCAL_VLM_RESERVE_SECONDS)))


def mesh_local_budget(started, cap=80):
    # Local fallback receives the actual remaining budget, not a post-provider residue.
    return max(2.0, min(float(cap), mesh_remaining(started)))
'''
    text = replace_once(text, anchor, anchor + insertion, 'SESSION_INSERT')

    text = replace_once(
        text,
        "event={'timestamp':time.time(),'elapsed_seconds':round(time.monotonic()-STARTED,2),**data,",
        "event={'timestamp':time.time(),'session_id':CURRENT_SESSION_KEY,'elapsed_seconds':round(time.monotonic()-STARTED,2),**data,",
        'LOG_SESSION',
    )

    text = replace_once(text, 'def request_gateway(body):', 'def request_gateway(body, timeout=75):', 'GATEWAY_SIG')
    text = replace_once(
        text,
        "with urllib.request.urlopen(req,timeout=75) as res:return res.status,json.loads(res.read())",
        "with urllib.request.urlopen(req,timeout=max(2,min(float(timeout),75))) as res:return res.status,json.loads(res.read())",
        'GATEWAY_TIMEOUT',
    )

    text = text.replace("max(2,min(55,105-(time.monotonic()-started)))", "mesh_external_budget(started,55)")
    text = text.replace("max(2,min(80,105-(time.monotonic()-started)))", "mesh_local_budget(started,80)")
    text = text.replace("remaining=max(2,min(45,105-(time.monotonic()-started)))", "remaining=mesh_external_budget(started,45)")
    text = replace_once(
        text,
        "body['request_budget_ms']=max(1000,min(60000,int((105-(time.monotonic()-started))*1000)))",
        "body['request_budget_ms']=max(1000,min(60000,int(mesh_external_budget(started,60)*1000)))",
        'REQUEST_BUDGET',
    )

    old_order = '''    response=router()\n    if response:return response\n    response=groq_router()\n    if response:return response\n    body['request_budget_ms']=max(1000,min(60000,int(mesh_external_budget(started,60)*1000)))\n    http,data=request_gateway(body)\n    if http==200 and isinstance(data,dict) and data.get('ok') is True:\n        if router_attempts:data['provider_attempts']=(data.get('provider_attempts') or [])+router_attempts\n        return http,data\n    gateway_attempts=(data.get('provider_attempts') or []) if isinstance(data,dict) else []\n    response=text_router()\n    if response:\n        response[1]['provider_attempts']=gateway_attempts+router_attempts\n        return response\n    response=local_router()\n    if response:\n        response[1]['provider_attempts']=gateway_attempts+router_attempts\n        return response\n'''
    new_order = '''    response=router()\n    if response:return response\n    response=groq_router()\n    if response:return response\n    # Quota-independent local VLM runs before the long remote gateway.\n    # External providers cannot consume its reserved budget.\n    response=local_router()\n    if response:return response\n    body['request_budget_ms']=max(1000,min(60000,int(mesh_external_budget(started,60)*1000)))\n    gateway_timeout=mesh_external_budget(started,GATEWAY_TIMEOUT_CAP_SECONDS)\n    http,data=request_gateway(body,timeout=gateway_timeout)\n    if http==200 and isinstance(data,dict) and data.get('ok') is True:\n        if router_attempts:data['provider_attempts']=(data.get('provider_attempts') or [])+router_attempts\n        return http,data\n    gateway_attempts=(data.get('provider_attempts') or []) if isinstance(data,dict) else []\n    response=text_router()\n    if response:\n        response[1]['provider_attempts']=gateway_attempts+router_attempts\n        return response\n'''
    text = replace_once(text, old_order, new_order, 'ROUTE_ORDER')

    old_exhausted = '''    return 503,{'status':'FREE_MESH_EXHAUSTED_CURRENT_CYCLE',\n                'provider_attempts':gateway_attempts+router_attempts,\n                'mandatory_cost_usd':0,'paid_fallback_used':False}\n'''
    new_exhausted = '''    attempts=gateway_attempts+router_attempts\n    local_transient=any(a.get('route')=='local-cloud-vlm' and a.get('status') in\n                        ('local_model_error','budget_exceeded') for a in attempts)\n    return 503,{'status':'LOCAL_TRANSIENT_FAILURE_CURRENT_CYCLE' if local_transient else 'FREE_MESH_EXHAUSTED_CURRENT_CYCLE',\n                'provider_attempts':attempts,\n                'mandatory_cost_usd':0,'paid_fallback_used':False}\n'''
    text = replace_once(text, old_exhausted, new_exhausted, 'EXHAUSTED_CAUSE')

    text = replace_once(
        text,
        '    policy_rejections=0\n    provider_capacity_cycles=0\n',
        '    policy_rejections=0\n    provider_capacity_cycles=0\n    local_transient_cycles=0\n',
        'TRANSIENT_COUNTER',
    )

    capacity_anchor = "        if data.get('status') in LOCAL_FALLBACK_CAPACITY_STATUSES | {'LOCAL_ACTION_UNAVAILABLE','FREE_MESH_EXHAUSTED_CURRENT_CYCLE'}:\n"
    transient_handler = "        if data.get('status')=='LOCAL_TRANSIENT_FAILURE_CURRENT_CYCLE':\n            local_transient_cycles+=1\n            body['provider_hint']='text' if attempt else 'openrouter'\n            log_event({'status':'LOCAL_TRANSIENT_RETRY','attempt':attempt+1,'reason':data.get('status')})\n            time.sleep(min(2,attempt+1))\n            continue\n"
    text = replace_once(text, capacity_anchor, transient_handler + capacity_anchor, 'TRANSIENT_HANDLER')

    final_anchor = '''    if policy_rejections and provider_capacity_cycles==0:\n        # Valid zero-cost model responses existed, but every candidate action\n        # violated the local action contract.  Preserve the true cause; never\n        # mislabel compiler/policy rejection as provider exhaustion.\n        return terminal('ACTION_CONTRACT_EXHAUSTED')\n'''
    final_new = final_anchor + "    if local_transient_cycles and provider_capacity_cycles==0:\n        return terminal('LOCAL_FALLBACK_TRANSIENT_EXHAUSTED')\n"
    text = replace_once(text, final_anchor, final_new, 'FINAL_CAUSE')

    text = replace_once(
        text,
        "        with LOCK:\n            try:\n",
        "        session_raw=self.headers.get('X-ARBM-Session-ID') or (os.environ.get('GITHUB_RUN_ID','local')+':'+os.environ.get('TASK_ID','unknown'))\n        with LOCK:\n            activate_session(session_raw)\n            try:\n",
        'HANDLER_SESSION',
    )

    old_main = '''if __name__=='__main__':\n    threading.Thread(target=heartbeat,daemon=True).start()\n    ThreadingHTTPServer(('127.0.0.1',8088),Handler).serve_forever()\n'''
    new_main = r'''def isolated_self_test(run_id, task, verify_budget=False, enforce_session_isolation=False):
    result={'status':'PASS','run_id':str(run_id),'task':str(task),'zero_spend':os.environ.get('ZERO_SPEND_MODE')=='HARD'}
    if not result['zero_spend']:
        raise SystemExit('ZERO_SPEND_MODE_HARD_REQUIRED')
    if verify_budget:
        now=time.monotonic()
        external_fresh=mesh_external_budget(now,55)
        local_fresh=mesh_local_budget(now,80)
        aged=now-(MESH_TOTAL_BUDGET_SECONDS-LOCAL_VLM_RESERVE_SECONDS-10)
        external_aged=mesh_external_budget(aged,55)
        local_aged=mesh_local_budget(aged,80)
        if external_fresh > MESH_TOTAL_BUDGET_SECONDS-LOCAL_VLM_RESERVE_SECONDS+0.01:
            raise SystemExit('EXTERNAL_BUDGET_CONSUMES_LOCAL_RESERVE')
        if local_aged <= external_aged:
            raise SystemExit('LOCAL_RESERVE_NOT_PRESERVED')
        result['budget']={'total_seconds':MESH_TOTAL_BUDGET_SECONDS,'local_reserve_seconds':LOCAL_VLM_RESERVE_SECONDS,
                          'external_fresh':round(external_fresh,3),'local_fresh':round(local_fresh,3),
                          'external_aged':round(external_aged,3),'local_aged':round(local_aged,3)}
    if enforce_session_isolation:
        a=f'{run_id}:{task}:session-a'; b=f'{run_id}:{task}:session-b'
        ka=activate_session(a); STATE['step']=17; STATE['memory'].append('session-a-proof')
        kb=activate_session(b)
        if STATE['step']!=0 or STATE['memory']:
            raise SystemExit('SESSION_B_INHERITED_SESSION_A')
        STATE['step']=91; STATE['memory'].append('session-b-proof')
        activate_session(a)
        if STATE['step']!=17 or STATE['memory']!=['session-a-proof']:
            raise SystemExit('SESSION_A_STATE_NOT_RESTORED')
        activate_session(b)
        if STATE['step']!=91 or STATE['memory']!=['session-b-proof']:
            raise SystemExit('SESSION_B_STATE_NOT_RESTORED')
        result['session_isolation']={'session_a':ka,'session_b':kb,'isolated':True}
    result['transient_failure_mapping']='LOCAL_FALLBACK_TRANSIENT_EXHAUSTED'
    print(json.dumps(result,sort_keys=True))
    return 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(add_help=True)
    parser.add_argument('--test-isolated-run',action='store_true')
    parser.add_argument('--run-id',default=os.environ.get('GITHUB_RUN_ID','local'))
    parser.add_argument('--task',default=os.environ.get('TASK_ID','unknown'))
    parser.add_argument('--verify-budget',action='store_true')
    parser.add_argument('--enforce-session-isolation',action='store_true')
    args=parser.parse_args()
    if args.test_isolated_run:
        raise SystemExit(isolated_self_test(args.run_id,args.task,args.verify_budget,args.enforce_session_isolation))
    threading.Thread(target=heartbeat,daemon=True).start()
    ThreadingHTTPServer(('127.0.0.1',8088),Handler).serve_forever()
'''
    text = replace_once(text, old_main, new_main, 'CLI_SELFTEST')
    return text


def patch_local(text: str) -> str:
    if LOCAL_MARKER in text:
        return text
    old = """    command=(blocks[-1] if blocks else raw).strip()\n    if re.match(r'(?:import\\s+pyautogui\\s*\\n)?\\s*pyautogui\\.',command):\n        return _local_action_grounding_gate(canonical_action({'action':'exec','command':command}))\n    raise ValueError('LOCAL_ACTION_REQUIRED')\n"""
    new = """    command=(blocks[-1] if blocks else raw).strip()\n    if re.match(r'(?:import\\s+pyautogui\\s*\\n)?\\s*pyautogui\\.',command):\n        return _local_action_grounding_gate(canonical_action({'action':'exec','command':command}))\n    # ARBM_LOCAL_VLM_PARSE_RECOVERY_V1\n    # Recover a single direct GUI call embedded in prose. canonical_action is\n    # still the executable security boundary, so this widens representation\n    # tolerance without widening the command allowlist.\n    calls=re.findall(r\"pyautogui\\.(?:click|doubleClick|rightClick|moveTo|press|hotkey|write|typewrite|scroll|sleep|mouseDown|mouseUp|dragTo|keyDown|keyUp)\\s*\\([^\\n`]*\\)\",raw)\n    for candidate in reversed(calls):\n        try:\n            return _local_action_grounding_gate(canonical_action({'action':'exec','command':candidate.strip()}))\n        except ValueError:\n            continue\n    raise ValueError('LOCAL_ACTION_REQUIRED')\n"""
    return replace_once(text, old, new, 'LOCAL_PARSE_RECOVERY')


def main():
    before = {}
    after = {}
    for path, patcher in ((SHIM, patch_shim), (LOCAL, patch_local)):
        raw = path.read_text(encoding='utf-8')
        before[str(path)] = hashlib.sha256(raw.encode()).hexdigest()
        patched = patcher(raw)
        path.write_text(patched, encoding='utf-8')
        after[str(path)] = hashlib.sha256(patched.encode()).hexdigest()
    print('PATCH_SHIM_MESH=PASS')
    for path in before:
        print(f'{path}: {before[path]} -> {after[path]}')


if __name__ == '__main__':
    main()
