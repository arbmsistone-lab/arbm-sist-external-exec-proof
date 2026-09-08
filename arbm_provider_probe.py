import json,os,urllib.request,urllib.error
API='https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v5'
CASES=[('google','gemini-3.6-flash'),('google','gemini-3.5-flash'),('google','gemini-3.5-flash-lite'),('google','gemini-3.1-flash-lite'),('groq','qwen/qwen3.8-27b'),('groq','qwen/qwen3.6-27b'),('groq','openai/gpt-oss-120b'),('groq','openai/gpt-oss-20b')]
def oidc():
 u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']; t=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']; sep='&' if '?' in u else '?'
 with urllib.request.urlopen(urllib.request.Request(u+sep+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+t}),timeout=20) as r:return json.loads(r.read())['value']
def one(provider,model):
 body={'instruction':'Return one safe first bash command as JSON.','observation':'No commands executed yet.','step':1,'provider_hint':provider,'model_hint':model}
 req=urllib.request.Request(API,data=json.dumps(body).encode(),method='POST',headers={'Authorization':'Bearer '+oidc(),'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=45) as r:d=json.loads(r.read()); return {'provider':provider,'model':model,'http':r.status,'ok':d.get('ok'),'used_model':d.get('model'),'attempts':d.get('provider_attempts'),'cost':d.get('mandatory_cost_usd'),'paid':d.get('paid_fallback_used')}
 except urllib.error.HTTPError as e:
  d=json.loads(e.read()); return {'provider':provider,'model':model,'http':e.code,'ok':False,'attempts':d.get('provider_attempts'),'cost':d.get('mandatory_cost_usd')}
rows=[one(*c) for c in CASES]; print(json.dumps(rows,separators=(',',':')))
live=[r for r in rows if r.get('ok') is True and r.get('cost')==0 and r.get('paid') is False]
print(json.dumps({'tested':len(rows),'live':len(live),'live_models':[r['model'] for r in live],'mandatory_cost_usd':0},separators=(',',':')))
if not live: raise SystemExit(2)
