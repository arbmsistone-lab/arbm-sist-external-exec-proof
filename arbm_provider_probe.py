import json,os,urllib.request,urllib.error
API='https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v7'
MODELS=['@cf/ibm-granite/granite-4.0-h-micro','@cf/zai-org/glm-4.7-flash','@cf/qwen/qwen3-30b-a3b-fp8']
def oidc():
 u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']; t=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']; sep='&' if '?' in u else '?'
 with urllib.request.urlopen(urllib.request.Request(u+sep+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+t}),timeout=20) as r:return json.loads(r.read())['value']
def one(model):
 body={'instruction':'Return one safe first bash inspection command as JSON.','observation':'No commands executed yet.','step':1,'provider_hint':'cloudflare','model_hint':model}
 req=urllib.request.Request(API,data=json.dumps(body).encode(),method='POST',headers={'Authorization':'Bearer '+oidc(),'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=45) as r:d=json.loads(r.read()); return {'hint':model,'http':r.status,'ok':d.get('ok'),'provider':d.get('provider'),'used_model':d.get('model'),'attempts':d.get('provider_attempts'),'cost':d.get('mandatory_cost_usd'),'paid':d.get('paid_fallback_used')}
 except urllib.error.HTTPError as e:
  d=json.loads(e.read()); return {'hint':model,'http':e.code,'ok':False,'attempts':d.get('provider_attempts'),'cost':d.get('mandatory_cost_usd')}
rows=[one(m) for m in MODELS]; print(json.dumps(rows,separators=(',',':')))
respected=[r for r in rows if r.get('ok') is True and r.get('used_model')==r.get('hint') and r.get('cost')==0 and r.get('paid') is False]
print(json.dumps({'tested':len(rows),'respected':len(respected),'models':[r['hint'] for r in respected],'mandatory_cost_usd':0},separators=(',',':')))
if not any(r.get('ok') is True for r in rows): raise SystemExit(2)