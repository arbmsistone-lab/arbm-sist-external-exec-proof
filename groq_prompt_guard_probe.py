import json, os, urllib.request
URL='https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-ai-three-provider-probe-20260908'
u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']; t=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']
sep='&' if '?' in u else '?'
r=urllib.request.Request(u+sep+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+t})
with urllib.request.urlopen(r,timeout=20) as x: oidc=json.loads(x.read())['value']
req=urllib.request.Request(URL,data=b'{}',method='POST',headers={'Authorization':'Bearer '+oidc,'Content-Type':'application/json'})
with urllib.request.urlopen(req,timeout=30) as x: data=json.loads(x.read())
print(json.dumps(data,separators=(',',':')))
if data.get('status')!='PASS' or data.get('certified_tokens_per_day')!=1000000: raise SystemExit(2)
