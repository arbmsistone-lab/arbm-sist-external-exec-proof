"""Safe provider-secret presence inventory through existing Supabase OIDC edge function."""
import json, os, urllib.request, urllib.error
URL='https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-ai-three-provider-probe-20260908'
ALLOWED=('COHERE_API_KEY','OPENROUTER_API_KEY','SAMBANOVA_API_KEY','CEREBRAS_API_KEY','NVIDIA_API_KEY','NVCF_RUN_KEY','SCW_SECRET_KEY','SCW_ACCESS_KEY','POLLINATIONS_API_KEY','HF_TOKEN','GEMINI_API_KEY','GROQ_API_KEY','LIGHTNING_API_KEY','MISTRAL_API_KEY')

def oidc():
    u=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']; t=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']
    sep='&' if '?' in u else '?'
    req=urllib.request.Request(u+sep+'audience=arbm-sist-benchmark',headers={'Authorization':'Bearer '+t})
    with urllib.request.urlopen(req,timeout=20) as r: return json.loads(r.read())['value']

def main():
    tok=oidc(); body=json.dumps({'mode':'inventory'}).encode()
    req=urllib.request.Request(URL,data=body,method='POST',headers={'Authorization':'Bearer '+tok,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req,timeout=30) as r: http=r.status; data=json.loads(r.read())
    except urllib.error.HTTPError as e:
        http=e.code; data=json.loads(e.read() or b'{}')
    present=data.get('present') or {}; safe={k:bool(present.get(k)) for k in ALLOWED}
    print(json.dumps({'status':data.get('status'),'edge_http':http,'present':safe,'values_exposed':False},separators=(',',':')))
    return 0 if http==200 and data.get('status')=='PASS' and data.get('values_exposed') is False else 2

if __name__=='__main__': raise SystemExit(main())
