import json, os, urllib.error, urllib.request
API='https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-ai-three-provider-probe-20260908'

def oidc():
    url=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']
    tok=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']
    sep='&' if '?' in url else '?'
    req=urllib.request.Request(url+sep+'audience=arbm-sist-benchmark', headers={'Authorization':'Bearer '+tok})
    with urllib.request.urlopen(req,timeout=20) as r:
        return json.loads(r.read())['value']

def main():
    if os.environ.get('ZERO_SPEND_MODE')!='HARD': raise SystemExit('ZERO_SPEND_HARD_REQUIRED')
    req=urllib.request.Request(API,data=b'{}',method='POST',headers={'Authorization':'Bearer '+oidc(),'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            data=json.loads(r.read()); http=r.status
    except urllib.error.HTTPError as e:
        http=e.code
        try: data=json.loads(e.read())
        except Exception: data={'status':'INVALID_RESPONSE'}
    safe={k:data.get(k) for k in ('provider','status','http','requests_per_second','limits','mandatory_cost_usd','paid_fallback_used','github_run_id') if k in data}
    print(json.dumps({'http':http,'response':safe},separators=(',',':')))
if __name__=='__main__': main()
