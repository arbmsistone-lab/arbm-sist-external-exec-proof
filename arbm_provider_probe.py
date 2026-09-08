import json,os,urllib.request,urllib.error
API='https://arbm-p0-free-proof.zevanory.workers.dev'; MODEL='@cf/nvidia/nemotron-3-120b-a12b'
def oidc():
 u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']; t=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']; sep='&' if '?' in u else '?'
 with urllib.request.urlopen(urllib.request.Request(u+sep+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+t,'User-Agent':'curl/8.5.0'}),timeout=20) as r:return json.loads(r.read())['value']
token=oidc(); body={'model':MODEL,'messages':[{'role':'user','content':'Reply only ARBM_CF_OIDC_PASS'}]}
req=urllib.request.Request(API,data=json.dumps(body).encode(),method='POST',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','Accept':'application/json','User-Agent':'curl/8.5.0'})
try:
 with urllib.request.urlopen(req,timeout=45) as r:d=json.loads(r.read()); txt=str((((d.get('result') or {}).get('choices') or [{}])[0].get('message') or {}).get('content') or ''); out={'http':r.status,'ok':d.get('ok'),'provider':d.get('provider'),'model':d.get('model'),'matched':'ARBM_CF_OIDC_PASS' in txt,'cost':d.get('mandatory_cost_usd'),'paid':d.get('paid_fallback_used')}
except urllib.error.HTTPError as e: out={'http':e.code,'ok':False,'error':e.read().decode('utf-8','replace')[:200]}
print(json.dumps(out,separators=(',',':')))
if not(out.get('http')==200 and out.get('ok') is True and out.get('cost')==0 and out.get('paid') is False): raise SystemExit(2)