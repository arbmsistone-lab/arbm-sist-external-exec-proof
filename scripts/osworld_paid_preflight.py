"""Live admission for the explicit bounded paid G3 route."""
import base64
import json
import os
import sys
from pathlib import Path

from osworld_control import pack_payload
from osworld_openrouter_paid import PAID_ROUTE, DEFAULT_MODEL

root=Path(sys.argv[1])
pngs=sorted(root.glob('**/*.png'))
if not pngs:
    raise RuntimeError('REAL_RECORDED_SCREENSHOT_REQUIRED')
body,_=pack_payload({
    'instruction':'Choose one harmless visible GUI action and return the required JSON action contract.',
    'observation':'','screenshot_data_url':'data:image/png;base64,'+base64.b64encode(pngs[0].read_bytes()).decode(),
    'phase':'execute','step':1,'memory':'','previous_command':'','verified_milestones':[],
    'recovery_strategy':'Use one visible control only.','verifier':{}})
result,attempts=PAID_ROUTE.call(body,budget=55)
if not result:
    raise RuntimeError('PAID_ROUTE_ADMISSION_FAILED:'+json.dumps(attempts)[-2000:])
cost=float(result.get('mandatory_cost_usd') or 0)
cap=float(os.environ.get('ARBM_PAID_REQUEST_MAX_USD','0.05'))
if result.get('model')!=os.environ.get('ARBM_PAID_MODEL',DEFAULT_MODEL):
    raise RuntimeError('PAID_MODEL_MISMATCH')
if not (0 < cost <= cap) or result.get('paid_fallback_used') is not True:
    raise RuntimeError('PAID_COST_PROOF_INVALID')
out={'status':'LIVE_PAID_PROBE_PASS','model':result['model'],'provider':result['provider'],
     'mandatory_cost_usd':cost,'paid_fallback_used':True,'provider_attempts':attempts,
     'purpose':'provider admission only; no benchmark action executed'}
Path('osworld-v32-paid-preflight.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps({'status':out['status'],'model':out['model'],'cost_usd':cost}))
