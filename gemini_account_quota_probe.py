"""Account-bound Gemini live/quota metadata probe through Supabase OIDC."""
import json, os, urllib.request, urllib.error
URL='https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-ai-three-provider-probe-20260908'

def oidc():
    u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']; t=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']
    sep='&' if '?' in u else '?'
    req=urllib.request.Request(u+sep+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+t})
    with urllib.request.urlopen(req,timeout=20) as r: return json.loads(r.read())['value']

def main():
    tok=oidc(); body=json.dumps({'mode':'gemini'}).encode()
    req=urllib.request.Request(URL,data=body,method='POST',headers={'Authorization':'Bearer '+tok,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r: http=r.status; data=json.loads(r.read())
    except urllib.error.HTTPError as e:
        http=e.code; data=json.loads(e.read() or b'{}')
    safe={k:data.get(k) for k in ('status','http','model','parsed','matched','rate_limit_headers','error_code','error_status','error_message','mandatory_cost_usd','paid_fallback_used')}
    safe['edge_http']=http; print(json.dumps(safe,separators=(',',':')))
    return 0 if http==200 else 2

if __name__=='__main__': raise SystemExit(main())
