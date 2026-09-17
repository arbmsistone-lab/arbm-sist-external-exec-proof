#!/usr/bin/env python3
from pathlib import Path

P=Path('scripts/osworld_free_mesh_shim.py')
s=P.read_text(encoding='utf-8')
MARK='ARBM_TOP3_MESH_SESSION_BUDGET_V1'
if MARK in s:
    print('PATCH_SHIM_MESH_TOP3=ALREADY_APPLIED'); raise SystemExit(0)

def once(old,new,label):
    global s
    c=s.count(old)
    if c!=1: raise SystemExit(f'PATCH_CONTEXT_{label}_COUNT={c}')
    s=s.replace(old,new,1)

once('import json, os, time, urllib.request, urllib.error, hashlib, threading',
     'import argparse, json, os, time, urllib.request, urllib.error, hashlib, threading','IMPORT')

anchor='STOP = threading.Event()\n'
insert=r'''

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
'''
once(anchor,anchor+insert,'INSERT')

once("event={'timestamp':time.time(),'elapsed_seconds':round(time.monotonic()-STARTED,2),**data,",
     "event={'timestamp':time.time(),'session_id':CURRENT_SESSION_KEY,'elapsed_seconds':round(time.monotonic()-STARTED,2),**data,",'LOG_SESSION')
once('def request_gateway(body):','def request_gateway(body, timeout=75):','GW_SIG')
once("with urllib.request.urlopen(req,timeout=75) as res:return res.status,json.loads(res.read())",
     "with urllib.request.urlopen(req,timeout=max(2,min(float(timeout),75))) as res:return res.status,json.loads(res.read())",'GW_TIMEOUT')

s=s.replace("max(2,min(55,105-(time.monotonic()-started)))","mesh_external_budget(started,55)")
s=s.replace("max(2,min(80,105-(time.monotonic()-started)))","mesh_local_budget(started,80)")
s=s.replace("remaining=max(2,min(45,105-(time.monotonic()-started)))","remaining=mesh_external_budget(started,45)")
once("body['request_budget_ms']=max(1000,min(60000,int((105-(time.monotonic()-started))*1000)))",
     "body['request_budget_ms']=max(1000,min(60000,int(mesh_external_budget(started,60)*1000)))",'REQ_BUDGET')

old='''    response=router()\n    if response:return response\n    response=groq_router()\n    if response:return response\n    body['request_budget_ms']=max(1000,min(60000,int(mesh_external_budget(started,60)*1000)))\n    http,data=request_gateway(body)\n    if http==200 and isinstance(data,dict) and data.get('ok') is True:\n        if router_attempts:data['provider_attempts']=(data.get('provider_attempts') or [])+router_attempts\n        return http,data\n    gateway_attempts=(data.get('provider_attempts') or []) if isinstance(data,dict) else []\n    response=text_router()\n    if response:\n        response[1]['provider_attempts']=gateway_attempts+router_attempts\n        return response\n    response=local_router()\n    if response:\n        response[1]['provider_attempts']=gateway_attempts+router_attempts\n        return response\n'''
new='''    response=router()\n    if response:return response\n    response=groq_router()\n    if response:return response\n    # Preserve an independent quota-free path before the long remote gateway.\n    response=local_router()\n    if response:return response\n    body['request_budget_ms']=max(1000,min(60000,int(mesh_external_budget(started,60)*1000)))\n    http,data=request_gateway(body,timeout=mesh_external_budget(started,GATEWAY_TIMEOUT_CAP_SECONDS))\n    if http==200 and isinstance(data,dict) and data.get('ok') is True:\n        if router_attempts:data['provider_attempts']=(data.get('provider_attempts') or [])+router_attempts\n        return http,data\n    gateway_attempts=(data.get('provider_attempts') or []) if isinstance(data,dict) else []\n    response=text_router()\n    if response:\n        response[1]['provider_attempts']=gateway_attempts+router_attempts\n        return response\n'''
once(old,new,'ORDER')

old="""    all_attempts=gateway_attempts+router_attempts\n    if _local_contract_failure(all_attempts):\n        return 422,{'status':'LOCAL_ACTION_CONTRACT_EXHAUSTED','provider_attempts':all_attempts,\n                    'mandatory_cost_usd':0,'paid_fallback_used':False}\n    return 503,{'status':'FREE_MESH_EXHAUSTED_CURRENT_CYCLE',\n                'provider_attempts':all_attempts,\n                'mandatory_cost_usd':0,'paid_fallback_used':False}\n"""
new="""    all_attempts=gateway_attempts+router_attempts\n    if _local_contract_failure(all_attempts):\n        return 422,{'status':'LOCAL_ACTION_CONTRACT_EXHAUSTED','provider_attempts':all_attempts,\n                    'mandatory_cost_usd':0,'paid_fallback_used':False}\n    local_transient=any(a.get('route')=='local-cloud-vlm' and a.get('status') in ('local_model_error','budget_exceeded') for a in all_attempts)\n    return 503,{'status':'LOCAL_TRANSIENT_FAILURE_CURRENT_CYCLE' if local_transient else 'FREE_MESH_EXHAUSTED_CURRENT_CYCLE',\n                'provider_attempts':all_attempts,\n                'mandatory_cost_usd':0,'paid_fallback_used':False}\n"""
once(old,new,'CAUSE')

once('    policy_rejections=0; provider_capacity_cycles=0; local_contract_cycles=0\n',
     '    policy_rejections=0; provider_capacity_cycles=0; local_contract_cycles=0; local_transient_cycles=0\n','COUNTER')
cap="        if data.get('status') in LOCAL_FALLBACK_CAPACITY_STATUSES | {'FREE_MESH_EXHAUSTED_CURRENT_CYCLE'}:\n"
trans="        if data.get('status')=='LOCAL_TRANSIENT_FAILURE_CURRENT_CYCLE':\n            local_transient_cycles+=1; body['provider_hint']='text' if attempt==0 else 'openrouter'; log_event({'status':'LOCAL_TRANSIENT_RETRY','attempt':attempt+1}); continue\n"
once(cap,trans+cap,'TRANSIENT')
nonce="""    if local_contract_cycles or policy_rejections:\n        return terminal('ACTION_CONTRACT_EXHAUSTED')\n"""
once2=nonce+"    if local_transient_cycles and provider_capacity_cycles==0:\n        return terminal('LOCAL_FALLBACK_TRANSIENT_EXHAUSTED')\n"
once(nonce,nonce2,'FINAL_CAUSE')

once("        self.close_connection=True; self.connection.settimeout(60)\n        with LOCK:\n            try:\n",
     "        self.close_connection=True; self.connection.settimeout(60)\n        session_raw=self.headers.get('X-ARBM-Session-ID') or (os.environ.get('GITHUB_RUN_ID','local')+':'+os.environ.get('TASK_ID','unknown'))\n        with LOCK:\n            activate_session(session_raw)\n            try:\n",'SESSION_HANDLER')

oldmain="""if __name__=='__main__':\n    threading.Thread(target=heartbeat,daemon=True).start()\n    if os.environ.get('ZERO_SPEND_MODE')=='HARD' and os.environ.get('ARBM_ENABLE_LOCAL_VLM')=='1':\n        threading.Thread(target=warm_runtime,daemon=True,name='arbm-local-vlm-warmup').start()\n    ThreadingHTTPServer(('127.0.0.1',8088),Handler).serve_forever()\n"""
newmain=r'''def isolated_self_test(run_id,task,verify_budget=False,enforce_session_isolation=False):
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
'''
once(oldmain,newmain,'MAIN')
P.write_text(s,encoding='utf-8'); print('PATCH_SHIM_MESH_TOP3=PASS')
