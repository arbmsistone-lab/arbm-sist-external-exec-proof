import argparse, json, sys
from pathlib import Path
from osworld_v32_policy import extract_state, enforce_policy, decision_from_agent
import osworld_free_mesh_shim as shim
from osworld_mesh_preflight import PNG_1X1

STRATEGIES = [
    'foreground-proof','archive-lock','verified-noop','capacity-hold',
    'planner-default','planner-mistral-first','planner-text-first',
    'reviewer-advisory','policy-replan','build-parity'
]

def base_body():
    return {'instruction':"Activate the focused OK button with pyautogui.press('enter').",
            'observation':'push-button OK focused','screenshot_data_url':'data:image/png;base64,'+PNG_1X1,
            'step':1,'memory':'','expected_build':shim.EXPECTED_BUILD}

def live(body):
    packed,metrics=shim.pack_payload(body)
    http,data=shim.request_mesh(packed)
    return http,data,metrics
def run_strategy(name):
    if name=='foreground-proof':
        st=extract_state('Chrome','label degree_audit_report.pdf')
        try: enforce_policy(st,{'kind':'NOOP_VERIFIED','checkpoint':{'visible_text':'degree_audit_report.pdf'}})
        except ValueError as e: return {'pass':'NOOP_REQUIRES_FOREGROUND_PROOF' in str(e),'detail':str(e)}
    if name=='archive-lock':
        st=extract_state('Archive Manager','title filter.zip\nlabel city.zip')
        try: enforce_policy(st,{'kind':'EXEC','command':"pyautogui.hotkey('ctrl','win','d')",'checkpoint':{'application':'Desktop'}})
        except ValueError as e: return {'pass':'SOURCE_CONTEXT_LOCKED' in str(e),'detail':str(e)}
    if name=='verified-noop':
        st=extract_state('Desktop','label\tdegree_audit_report.pdf')
        out=enforce_policy(st,{'kind':'NOOP_VERIFIED','checkpoint':{'visible_text':'degree_audit_report.pdf'}})
        return {'pass':out['kind']=='NOOP_VERIFIED','detail':out}
    if name=='capacity-hold':
        st=extract_state('Desktop','label x.pdf')
        out=decision_from_agent({'action':'exec','command':"pyautogui.press('enter')"},st,provider_available=False)
        return {'pass':out['kind']=='HOLD_CAPACITY','detail':out}
    if name in ('planner-default','planner-mistral-first','planner-text-first'):
        body=base_body()
        if name=='planner-mistral-first': body['provider_hint']='mistral'
        if name=='planner-text-first': body['provider_hint']='text'
        http,data,metrics=live(body)
        ok=http in (200,409) and data.get('mandatory_cost_usd')==0 and data.get('paid_fallback_used') is False
        return {'pass':ok,'http':http,'status':data.get('status'),'provider':data.get('provider'),'model':data.get('model'),'attempts':data.get('provider_attempts',[]),'payload':metrics}
    if name=='reviewer-advisory':
        body=base_body();body.update({'instruction':'Read source before opening Calendar','active_application':'Mail','observation':'attachment control','phase':'plan'})
        http,data,metrics=live(body)
        ok=http in (200,409,503) and all(a.get('role')!='transition-reviewer' for a in data.get('provider_attempts',[]))
        return {'pass':ok,'http':http,'status':data.get('status'),'transition_review':data.get('transition_review'),'attempts':data.get('provider_attempts',[])}
    if name=='policy-replan':
        body=base_body();body['memory']='POLICY REJECTED: SOURCE_CONTEXT_LOCKED. Replan within deterministic v32 constraints.'
        http,data,metrics=live(body)
        return {'pass':http in (200,409),'http':http,'status':data.get('status'),'provider':data.get('provider'),'model':data.get('model')}
    if name=='build-parity':
        http,data,metrics=live(base_body())
        ok=data.get('pipeline')==shim.EXPECTED_PIPELINE and data.get('agent_build')==shim.EXPECTED_BUILD
        return {'pass':ok,'http':http,'pipeline':data.get('pipeline'),'build':data.get('agent_build')}
    return {'pass':False,'detail':'unknown_strategy'}
def main():
    p=argparse.ArgumentParser();p.add_argument('strategy',choices=STRATEGIES);a=p.parse_args()
    result={'strategy':a.strategy}
    try:
        result.update(run_strategy(a.strategy));result.setdefault('error',None)
    except Exception as exc:
        result.update({'pass':False,'error':type(exc).__name__+':'+str(exc)})
    out=Path('matrix-results');out.mkdir(exist_ok=True)
    (out/(a.strategy+'.json')).write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
    print(json.dumps(result,default=str))

if __name__=='__main__':
    main()
