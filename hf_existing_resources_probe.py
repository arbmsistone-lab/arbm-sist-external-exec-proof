"""Read-only Hugging Face account/resource probe. Never creates or mutates resources."""
import json, os, urllib.request
TOKEN=os.environ.get('HF_TOKEN','').strip()
HEAD={'Authorization':'Bearer '+TOKEN,'User-Agent':'ARBM-capacity-audit/1.0'}
def get(url):
    req=urllib.request.Request(url,headers=HEAD)
    try:
        with urllib.request.urlopen(req,timeout=20) as r:return r.status,json.loads(r.read())
    except Exception as e:return getattr(e,'code',None),None

def main():
    if not TOKEN:
        print(json.dumps({'status':'NOT_CONFIGURED'})); return 0
    http,me=get('https://huggingface.co/api/whoami-v2')
    name=(me or {}).get('name'); acct=(me or {}).get('type') or (me or {}).get('auth',{}).get('type')
    spaces=[]
    if name:
        h,rows=get('https://huggingface.co/api/spaces?author='+name+'&limit=100')
        if h==200 and isinstance(rows,list):
            spaces=[{'id':x.get('id'),'private':x.get('private'),'sdk':x.get('sdk'),'likes':x.get('likes')} for x in rows[:30]]
    print(json.dumps({'status':'PASS' if http==200 else 'UNPROVEN','http':http,'account_type':acct,'space_count':len(spaces),'spaces':spaces,'values_exposed':False},separators=(',',':')))
    return 0
if __name__=='__main__': raise SystemExit(main())
