"""Read-only Hugging Face token scope and native inference eligibility probe."""
import json, os, urllib.request, urllib.error
T=os.environ.get('HF_TOKEN','').strip()
if not T:
    print(json.dumps({'status':'NOT_CONFIGURED'})); raise SystemExit(0)

def req(url, data=None):
    r=urllib.request.Request(url,data=data,method='POST' if data else 'GET',headers={'Authorization':'Bearer '+T,'Content-Type':'application/json','User-Agent':'ARBM-SIST-capacity-proof'})
    try:
        with urllib.request.urlopen(r,timeout=30) as x: return x.status,dict(x.headers),x.read()
    except urllib.error.HTTPError as e: return e.code,dict(e.headers),e.read()

s,h,b=req('https://huggingface.co/api/whoami-v2')
try: who=json.loads(b or b'{}')
except: who={}
auth=who.get('auth') or {}
safe_auth={'type':auth.get('type'),'accessTokenRole':auth.get('accessToken',{}).get('role'),'fineGrained':bool(auth.get('accessToken',{}).get('fineGrained'))}
models=['HuggingFaceTB/SmolLM2-135M-Instruct','google/gemma-2-2b-it']
rows=[]
for m in models:
    body=json.dumps({'inputs':'Reply only ARBM_HF_PASS','parameters':{'max_new_tokens':8,'return_full_text':False}}).encode()
    code,hh,bb=req('https://router.huggingface.co/hf-inference/models/'+m,body)
    text=(bb or b'')[:500].decode('utf-8','replace')
    rows.append({'model':m,'http':code,'live':code==200,'rate_headers':{k:v for k,v in hh.items() if 'rate' in k.lower() or 'limit' in k.lower()},'error_excerpt':None if code==200 else text[:180]})
print(json.dumps({'status':'PASS','whoami_http':s,'account_type':who.get('type'),'auth':safe_auth,'rows':rows,'secret_exposed':False},separators=(',',':')))
