import json, os, urllib.request, urllib.error
URL='https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-ai-three-provider-probe-20260908'

def oidc():
    u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']
    t=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']
    sep='&' if '?' in u else '?'
    r=urllib.request.Request(u+sep+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+t})
    with urllib.request.urlopen(r,timeout=20) as x:return json.loads(x.read())['value']

def main():
    if os.environ.get('ZERO_SPEND_MODE')!='HARD': raise SystemExit('ZERO_SPEND_HARD_REQUIRED')
    req=urllib.request.Request(URL,data=b'{}',method='POST',headers={'Authorization':'Bearer '+oidc(),'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r: data=json.loads(r.read())
    except urllib.error.HTTPError as e:
        data=json.loads(e.read() or b'{}')
    print(json.dumps(data,separators=(',',':')))
    if data.get('status')!='PASS' or data.get('certified_tokens_per_day')!=200000: raise SystemExit(2)
if __name__=='__main__': main()
