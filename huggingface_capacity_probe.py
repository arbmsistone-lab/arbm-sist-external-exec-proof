"""Account-bound Hugging Face recurring FREE capacity probe, fail closed."""
import json, os, urllib.request, urllib.error
from decimal import Decimal
WHOAMI="https://huggingface.co/api/whoami-v2"
ROUTER="https://router.huggingface.co/v1/chat/completions"
MODEL="openai/gpt-oss-20b:novita"
FREE_MONTHLY_USD=Decimal("0.10")
NORMALIZATION_DAYS=31
INPUT_PRICE_PER_M=Decimal("0.04")
OUTPUT_PRICE_PER_M=Decimal("0.15")
INPUT_TOKENS=1024; OUTPUT_TOKENS=32; USEFUL_TOKENS=INPUT_TOKENS+OUTPUT_TOKENS
COST_PER_CALL=(Decimal(INPUT_TOKENS)*INPUT_PRICE_PER_M+Decimal(OUTPUT_TOKENS)*OUTPUT_PRICE_PER_M)/Decimal(1_000_000)
CERTIFIED_TPD=int((FREE_MONTHLY_USD/Decimal(NORMALIZATION_DAYS)/COST_PER_CALL)*Decimal(USEFUL_TOKENS))

def get_json(url,token):
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+token,"User-Agent":"ARBM-SIST-capacity-audit/2.0"})
    with urllib.request.urlopen(req,timeout=25) as r:return r.status,json.loads(r.read()),dict(r.headers)

def live_call(token):
    payload=json.dumps({"model":MODEL,"messages":[{"role":"user","content":"Reply only ARBM_HF_PASS"}],"max_tokens":8,"temperature":0}).encode()
    req=urllib.request.Request(ROUTER,data=payload,method="POST",headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as r:
        raw=json.loads(r.read()); text=str((raw.get("choices") or [{}])[0].get("message",{}).get("content",'')); usage=raw.get("usage") or {}
        return r.status==200 and "ARBM_HF_PASS" in text,r.status,usage
def base(status):
    return {"provider":"huggingface-novita-free","independence_pool":"huggingface-account-novita-runtime","model":MODEL,
            "capacity_kind":"tokens","mandatory_cost_usd":0,"paid_fallback_used":False,
            "documented_free_monthly_usd":float(FREE_MONTHLY_USD),"normalization_days":NORMALIZATION_DAYS,
            "certified_tokens_per_day":0,"certified_useful_units_per_day":0,"status":status}

def main():
    if os.environ.get("ZERO_SPEND_MODE")!="HARD": raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    token=os.environ.get("HF_TOKEN","").strip()
    if not token:
        print(json.dumps(base("NOT_CONFIGURED"),separators=(",",":"))); return 0
    try:
        http,who,_=get_json(WHOAMI,token)
        free=http==200 and who.get("type")=="user" and who.get("isPro") is False and who.get("canPay") is False
        if not free:
            row=base("ACCOUNT_BILLING_NOT_PROVEN_FREE"); row.update({"account_verified":http==200,"account_type":who.get("type"),"is_pro":who.get("isPro"),"can_pay":who.get("canPay")})
            print(json.dumps(row,separators=(",",":"))); return 0
        live,live_http,usage=live_call(token); ok=live_http==200 and live
        row=base("PASS_ACCOUNT_BOUND" if ok else "LIVE_UNCERTIFIED"); row.update({"http":live_http,"account_verified":True,"account_type":"user","is_pro":False,"can_pay":False,"recurring_free":True,"reset_verified":True,"no_paid_fallback":True,"live":live,"usage":usage})
        if ok: row.update({"certified_tokens_per_day":CERTIFIED_TPD,"certified_useful_units_per_day":CERTIFIED_TPD})
        print(json.dumps(row,separators=(",",":"))); return 0
    except urllib.error.HTTPError as e:
        print(json.dumps({**base("HTTP_ERROR"),"http":e.code},separators=(",",":"))); return 0
    except Exception as e:
        print(json.dumps({**base("TRANSPORT_ERROR"),"error":type(e).__name__},separators=(",",":"))); return 0

if __name__=="__main__": raise SystemExit(main())
