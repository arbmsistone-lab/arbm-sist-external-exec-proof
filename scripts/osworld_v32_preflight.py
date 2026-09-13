"""Live GitHub OIDC and zero-cost provider admission before cloud VM boot."""
import base64
import json
import os
from pathlib import Path
import time
from osworld_control import pack_payload, validate_response
import osworld_free_mesh_shim as shim


def main(root):
    if os.environ.get('ZERO_SPEND_MODE') != 'HARD': raise RuntimeError('HARD_MODE_REQUIRED')
    http, data = shim.request_mesh({})
    if http != 400 or data.get('error') != 'INSTRUCTION_REQUIRED':
        raise RuntimeError('LIVE_OIDC_REJECTED:' + json.dumps({'http':http,'data':data}))
    pngs = sorted(root.glob('**/task-001/results/**/tasks/001/*.png'))
    if not pngs: raise RuntimeError('REAL_RECORDED_SCREENSHOT_REQUIRED')
    body, metrics = pack_payload({'instruction':"Dismiss any open notification or menu with pyautogui.press('esc'). Do not open files. This is provider admission only.",
        'observation':'', 'screenshot_data_url':'data:image/png;base64,' + base64.b64encode(pngs[0].read_bytes()).decode(),
        'expected_build':shim.EXPECTED_BUILD, 'phase':'execute','step':1,'memory':'', 'verified_milestones':[]})
    third_result,third_attempts=shim.FREE_ROUTE.call(body,budget=100)
    third_proof={'status':'LIVE_FREE_PROBE_PASS' if third_result else 'UNAVAILABLE',
                 'purpose':'provider admission only; no benchmark action executed',
                 'result':third_result,'attempts':third_attempts}
    mistral_body={**body,'provider_hint':'mistral','request_budget_ms':60000,
        'route_cooldowns':{route+':'+model:int((time.time()+120)*1000)
            for route,models in [('groq-multimodal-free',['qwen/qwen3.8-27b','qwen/qwen3.6-27b']),
                                 ('groq-accessibility-free',['openai/gpt-oss-120b','openai/gpt-oss-20b'])]
            for model in models}}
    mistral_http,mistral_data=shim.request_gateway(mistral_body)
    mistral_proof={'http':mistral_http,'data':mistral_data,
        'status':'UNAVAILABLE','purpose':'independent Mistral admission; not benchmark evidence'}
    if mistral_http==200:
        validate_response(mistral_data,shim.EXPECTED_PIPELINE,shim.EXPECTED_BUILD)
        if mistral_data.get('provider')!='mistral-free': raise RuntimeError('INDEPENDENT_MISTRAL_ROUTE_MISMATCH')
        mistral_proof['status']='LIVE_FREE_PROBE_PASS'
    failover_http,failover_data=shim.request_mesh(mistral_body)
    failover_proof={'http':failover_http,'data':failover_data,
        'purpose':'real independent FREE route failover admission; not benchmark evidence'}
    if failover_http==200: validate_response(failover_data,shim.EXPECTED_PIPELINE,shim.EXPECTED_BUILD)
    judge_messages=[{'role':'system','content':'You are a strict binary classifier. Output MUST be exactly one token: YES or NO. No punctuation, no extra words, no explanations.'},
        {'role':'user','content':[{'type':'text','text':'Does this image show a full-screen photograph of a football field with football players? Answer only YES or NO.'},
            {'type':'image_url','image_url':{'url':body['screenshot_data_url'],'detail':'high'}}]}]
    judge_result,judge_attempts=shim.FREE_ROUTE.call({},budget=100,raw_messages=judge_messages,raw_tokens=10)
    judge_proof={'purpose':'negative binary model-client admission using real recorded desktop; not a benchmark score',
        'result':judge_result,'attempts':judge_attempts,'status':'UNAVAILABLE'}
    if judge_result and judge_result['text'].strip()=='NO':judge_proof['status']='LIVE_FREE_NEGATIVE_BINARY_PASS'
    Path('osworld-v32-judge-admission.json').write_text(json.dumps(judge_proof,indent=2))
    if judge_proof['status']!='LIVE_FREE_NEGATIVE_BINARY_PASS':raise RuntimeError('FREE_JUDGE_BINARY_ADMISSION_FAILED')
    attempts=[]
    for attempt in range(3):
        http, data = shim.request_mesh(body)
        attempts.append({'http':http,'data':data,'payload':metrics})
        Path('osworld-v32-live-preflight.json').write_text(json.dumps({'screenshot_source_run':34733419571,
            'purpose':'provider admission only; not a benchmark result','candidate_sha':os.environ['GITHUB_SHA'],
            'oidc':'PASS','third_provider':third_proof,'mistral_provider':mistral_proof,
            'free_failover':failover_proof,'judge_provider':judge_proof,'attempts':attempts},indent=2))
        if http == 200:
            validate_response(data,shim.EXPECTED_PIPELINE,shim.EXPECTED_BUILD)
            if data.get('github_sha') != os.environ['GITHUB_SHA']: raise RuntimeError('OIDC_SHA_MISMATCH')
            print('LIVE_OIDC_AND_FREE_PROVIDER_PASS'); return
        if http == 409 and data.get('status') == 'REPLAN_REQUIRED':
            validate_response(data,shim.EXPECTED_PIPELINE,shim.EXPECTED_BUILD)
            body['memory']='Independent review requires replanning: ' + str(data.get('review_reason'))
            continue
        if http not in (429,503): break
        time.sleep(25)
    raise RuntimeError('LIVE_FREE_CAPACITY_NOT_PROVEN:' + json.dumps(attempts))


if __name__ == '__main__':
    import sys
    main(Path(sys.argv[1]))
