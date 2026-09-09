"""Daily public-contract drift probe for certified ZERO_SPEND capacity."""
import json, urllib.request

CHECKS={
 'cloudflare':('https://developers.cloudflare.com/workers-ai/platform/pricing/',('10,000 Neurons per day','reset daily at 00:00 UTC')),
 'groq':('https://console.groq.com/docs/rate-limits',('llama-prompt-guard-2-22m','500K','gpt-oss-20b','200K')),
 'mistral':('https://docs.mistral.ai/models/mistral-moderation-26-03',('mistral-moderation-2603','Price','Free')),
 'supabase':('https://supabase.com/docs/guides/platform/compute-and-disk',('Nano','$0','Free Plan')),
}

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'ARBM-SIST-capacity-contract-audit/1.0','Accept':'text/html,text/plain'})
    with urllib.request.urlopen(req,timeout=25) as r: return r.status,r.read().decode('utf-8','ignore')

def probe(fetcher=fetch):
    rows=[]
    for name,(url,needles) in CHECKS.items():
        try:
            http,text=fetcher(url); missing=[x for x in needles if x.lower() not in text.lower()]
            ok=http==200 and not missing
            rows.append({'name':name,'http':http,'status':'PASS' if ok else 'DRIFT','missing':missing})
        except Exception as e:
            rows.append({'name':name,'http':None,'status':'UNREACHABLE','error':type(e).__name__})
    return {'status':'PASS' if all(x['status']=='PASS' for x in rows) else 'FAIL','checks':rows}

def main():
    out=probe(); print(json.dumps(out,separators=(',',':')))
    return 0 if out['status']=='PASS' else 2

if __name__=='__main__': raise SystemExit(main())
