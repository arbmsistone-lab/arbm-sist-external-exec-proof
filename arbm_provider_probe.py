import json,os,urllib.request,urllib.error
API='https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v7'
def oidc():
    u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']; t=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']; sep='&' if '?' in u else '?'
    with urllib.request.urlopen(urllib.request.Request(u+sep+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+t}),timeout=20) as r:return json.loads(r.read())['value']
def call(step):
    body={'instruction':'Return one safe inspection command as JSON.','observation':'No commands executed yet.','step':step}
    req=urllib.request.Request(API,data=json.dumps(body).encode(),method='POST',headers={'Authorization':'Bearer '+oidc(),'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=40) as r:d=json.loads(r.read()); code=r.status
    except urllib.error.HTTPError as e:d=json.loads(e.read()); code=e.code
    return {'http':code,'provider':d.get('provider'),'model':d.get('model'),'attempts':d.get('provider_attempts') or [],'cost':d.get('mandatory_cost_usd'),'paid':d.get('paid_fallback_used')}
a=call(1); b=call(3)
print(json.dumps({'step1':a,'step3':b},separators=(',',':')))
if not(a['http']==200 and a['attempts'] and str(a['attempts'][0].get('route','')).startswith('lightning') and a['cost']==0 and a['paid'] is False): raise SystemExit(2)
if not(b['http']==200 and b['attempts'] and str(b['attempts'][0].get('route','')).startswith('groq') and b['cost']==0 and b['paid'] is False): raise SystemExit(3)
