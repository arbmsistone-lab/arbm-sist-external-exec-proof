import json,os,urllib.request,urllib.error
API='https://arbm-p0-free-proof.zevanory.workers.dev'
MODELS=['@cf/nvidia/nemotron-3-120b-a12b','@cf/ibm-granite/granite-4.0-h-micro','@cf/zai-org/glm-4.7-flash','@cf/qwen/qwen3-30b-a3b-fp8']
def oidc():
 u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']; t=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']; sep='&' if '?' in u else '?'
 with urllib.request.urlopen(urllib.request.Request(u+sep+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+t}),timeout=20) as r:return json.loads(r.read())['value']
def one(model,token):
 body={'model':model,'messages':[{'role':'user','content':'Reply only with ARBM_CF_CAPACITY_PASS'}],'max_tokens':32}
 req=urllib.request.Request(API,data=json.dumps(body).encode(),method='POST',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=45) as r:d=json.loads(r.read()); txt=str((((d.get('result') or {}).get('choices') or [{}])[0].get('message') or {}).get('content') or ''); return {'model':model,'http':r.status,'ok':d.get('ok'),'provider':d.get('provider'),'used_model':d.get('model'),'matched':'ARBM_CF_CAPACITY_PASS' in txt,'cost':d.get('mandatory_cost_usd'),'paid':d.get('paid_fallback_used')}
 except urllib.error.HTTPError as e:
  raw=e.read().decode('utf-8','replace')[:400]; return {'model':model,'http':e.code,'ok':False,'error':raw}
token=oidc(); rows=[one(m,token) for m in MODELS]; print(json.dumps(rows,separators=(',',':')))
live=[r for r in rows if r.get('http')==200 and r.get('ok') is True and r.get('cost')==0 and r.get('paid') is False]
print(json.dumps({'tested':len(rows),'live':len(live),'models':[r['model'] for r in live],'mandatory_cost_usd':0},separators=(',',':')))
if not live: raise SystemExit(2)