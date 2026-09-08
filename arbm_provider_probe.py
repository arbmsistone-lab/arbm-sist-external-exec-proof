import json,os,urllib.request,urllib.error
API='https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v7'
def oidc():
 u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']; t=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']; sep='&' if '?' in u else '?'
 with urllib.request.urlopen(urllib.request.Request(u+sep+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+t}),timeout=20) as r:return json.loads(r.read())['value']
body={'instruction':'Return one safe inspection command as JSON.','observation':'No commands executed yet.','step':1,'provider_hint':'lightning'}
req=urllib.request.Request(API,data=json.dumps(body).encode(),method='POST',headers={'Authorization':'Bearer '+oidc(),'Content-Type':'application/json'})
try:
 with urllib.request.urlopen(req,timeout=30) as r:d=json.loads(r.read()); out={'http':r.status,'ok':d.get('ok'),'attempts':d.get('provider_attempts'),'cost':d.get('mandatory_cost_usd'),'paid':d.get('paid_fallback_used')}
except urllib.error.HTTPError as e:
 d=json.loads(e.read()); out={'http':e.code,'ok':False,'status':d.get('status'),'attempts':d.get('provider_attempts'),'cost':d.get('mandatory_cost_usd'),'paid':d.get('paid_fallback_used')}
print(json.dumps(out,separators=(',',':')))
a=out.get('attempts') or []
if not(out.get('http')==503 and out.get('cost')==0 and out.get('paid') is False and any(x.get('route')=='lightning' and x.get('status')=='not_configured' for x in a)): raise SystemExit(2)