import json,os,urllib.request,urllib.error
API='https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v6'
CASES=[('google','gemini-3.6-flash'),('google','gemini-3.5-flash'),('google','gemini-3.5-flash-lite'),('google','gemini-3.1-flash-lite'),('groq','qwen/qwen3.8-27b'),('groq','qwen/qwen3.6-27b'),('groq','openai/gpt-oss-120b'),('groq','openai/gpt-oss-20b')]
def oidc():
 u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']; t=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']; sep='&' if '?' in u else '?'
 with urllib.request.urlopen(urllib.request.Request(u+sep+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+t}),timeout=20) as r:return json.loads(r.read())['value']
def call(body):
 req=urllib.request.Request(API,data=json.dumps(body).encode(),method='POST',headers={'Authorization':'Bearer '+oidc(),'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=45) as r:d=json.loads(r.read()); return r.status,d
 except urllib.error.HTTPError as e:return e.code,json.loads(e.read())
def forced(provider,model):
 http,d=call({'instruction':'Return one safe first bash command as JSON.','observation':'No commands executed yet.','step':1,'provider_hint':provider,'model_hint':model})
 return {'kind':'forced','provider':provider,'model':model,'http':http,'ok':d.get('ok'),'used_model':d.get('model'),'attempts':d.get('provider_attempts'),'cost':d.get('mandatory_cost_usd'),'paid':d.get('paid_fallback_used')}
def auto(step):
 http,d=call({'instruction':'Inspect the sandbox and choose one bounded safe bash command as JSON.','observation':'No commands executed yet.' if step==1 else 'Inspection completed successfully; choose the smallest verification or correction command.','step':step})
 return {'kind':'auto','step':step,'http':http,'ok':d.get('ok'),'provider':d.get('provider'),'model':d.get('model'),'attempts':d.get('provider_attempts'),'cost':d.get('mandatory_cost_usd'),'paid':d.get('paid_fallback_used')}
rows=[forced(*c) for c in CASES]+[auto(1),auto(3)]; print(json.dumps(rows,separators=(',',':')))
live=[r for r in rows[:8] if r.get('ok') is True and r.get('cost')==0 and r.get('paid') is False]
print(json.dumps({'forced_tested':8,'forced_live':len(live),'auto_step1_model':rows[8].get('model'),'auto_step3_model':rows[9].get('model'),'mandatory_cost_usd':0},separators=(',',':')))
if not live: raise SystemExit(2)