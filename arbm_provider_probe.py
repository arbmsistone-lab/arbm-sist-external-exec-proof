import json,os,urllib.request,urllib.error
API='https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v7'
def oidc():
 u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']; t=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']; sep='&' if '?' in u else '?'
 with urllib.request.urlopen(urllib.request.Request(u+sep+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+t}),timeout=20) as r:return json.loads(r.read())['value']
def auto(step):
 body={'instruction':'Inspect the sandbox and choose one bounded safe bash command as JSON.','observation':'No commands executed yet.' if step==1 else 'Inspection completed successfully; choose the smallest verification or correction command.','step':step}
 req=urllib.request.Request(API,data=json.dumps(body).encode(),method='POST',headers={'Authorization':'Bearer '+oidc(),'Content-Type':'application/json'})
 try:
  with urllib.request.urlopen(req,timeout=45) as r:d=json.loads(r.read()); return {'step':step,'http':r.status,'ok':d.get('ok'),'provider':d.get('provider'),'model':d.get('model'),'attempts':d.get('provider_attempts'),'cost':d.get('mandatory_cost_usd'),'paid':d.get('paid_fallback_used')}
 except urllib.error.HTTPError as e:
  d=json.loads(e.read()); return {'step':step,'http':e.code,'ok':False,'attempts':d.get('provider_attempts'),'cost':d.get('mandatory_cost_usd')}
rows=[auto(1),auto(3)]; print(json.dumps(rows,separators=(',',':')))
assert all(r.get('ok') is True and r.get('cost')==0 and r.get('paid') is False for r in rows)
assert rows[0].get('model') in {'gemini-3.5-flash-lite','gemini-3.1-flash-lite'}
assert rows[1].get('provider')=='groqcloud-free'
print(json.dumps({'status':'PASS','step1':rows[0].get('model'),'step3':rows[1].get('model'),'mandatory_cost_usd':0},separators=(',',':')))