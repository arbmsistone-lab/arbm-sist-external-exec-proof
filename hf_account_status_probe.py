"""Safe Hugging Face account-status proof. Never emits token."""
import json, os, urllib.request, urllib.error
T=os.environ.get('HF_TOKEN','').strip()
if not T:
    print(json.dumps({'status':'NOT_CONFIGURED'})); raise SystemExit(0)
req=urllib.request.Request('https://huggingface.co/api/whoami-v2',headers={'Authorization':'Bearer '+T,'User-Agent':'ARBM-SIST-capacity-proof'})
try:
    with urllib.request.urlopen(req,timeout=20) as r:
        d=json.loads(r.read() or b'{}')
        auth=d.get('auth') or {}; at=auth.get('accessToken') or {}
        out={'status':'PASS','http':r.status,'account_type':d.get('type'),'is_pro':d.get('isPro'),'can_pay':d.get('canPay'),'auth_type':auth.get('type'),'token_role':at.get('role'),'fine_grained':bool(at.get('fineGrained')),'secret_exposed':False}
        print(json.dumps(out,separators=(',',':')))
except urllib.error.HTTPError as e:
    print(json.dumps({'status':'HTTP_ERROR','http':e.code,'secret_exposed':False},separators=(',',':')))
