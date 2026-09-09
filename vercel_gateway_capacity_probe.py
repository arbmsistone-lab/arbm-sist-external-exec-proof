"""Fail-closed Vercel AI Gateway recurring-FREE capacity probe."""
import json, os, urllib.error, urllib.request
from decimal import Decimal
from pathlib import Path
API="https://ai-gateway.vercel.sh/v1/chat/completions"
DOC="https://vercel.com/ai-gateway/models/gpt-oss-20b"
MODEL="openai/gpt-oss-20b"
MONTHLY_CREDIT_USD=Decimal("5")
NORMALIZATION_DAYS=30
INPUT_PRICE_PER_M=Decimal("0.03")
OUTPUT_PRICE_PER_M=Decimal("0.14")
INPUT_TOKENS=1024
OUTPUT_TOKENS=32
USEFUL_TOKENS=INPUT_TOKENS+OUTPUT_TOKENS
COST_PER_CALL=(Decimal(INPUT_TOKENS)*INPUT_PRICE_PER_M+Decimal(OUTPUT_TOKENS)*OUTPUT_PRICE_PER_M)/Decimal(1_000_000)
CERTIFIED_TPD=int((MONTHLY_CREDIT_USD/Decimal(NORMALIZATION_DAYS)/COST_PER_CALL)*Decimal(USEFUL_TOKENS))

def account_proof():
    try:
        d=json.loads(Path("vercel-account-evidence.json").read_text(encoding="utf-8"))
        return d.get("plan")=="hobby" and d.get("mandatory_cost_usd")==0
    except Exception:
        return False

def docs_proof():
    try:
        req=urllib.request.Request(DOC,headers={"User-Agent":"ARBM-SIST-capacity-audit/1.0"})
        with urllib.request.urlopen(req,timeout=20) as r: text=r.read().decode("utf-8","ignore").lower()
        return ("$5" in text and "every 30 days" in text and "$0.03" in text and "$0.14" in text)
    except Exception:
        return False
def main():
    if os.environ.get("ZERO_SPEND_MODE")!="HARD": raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    key=os.environ.get("VERCEL_AI_GATEWAY_API_KEY","").strip()
    base={"provider":"vercel-ai-gateway-free","independence_pool":"vercel-team","model":MODEL,"mandatory_cost_usd":0,"paid_fallback_used":False,"documented_monthly_credit_usd":float(MONTHLY_CREDIT_USD),"normalization_days":NORMALIZATION_DAYS}
    if not key:
        print(json.dumps({**base,"status":"NOT_CONFIGURED","certified_tokens_per_day":0},separators=(",",":"))); return 0
    payload=json.dumps({"model":MODEL,"messages":[{"role":"user","content":"Reply only ARBM_VERCEL_PASS"}],"max_tokens":16,"temperature":0}).encode()
    req=urllib.request.Request(API,data=payload,method="POST",headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            body=json.loads(r.read().decode("utf-8")); text=str(body.get("choices",[{}])[0].get("message",{}).get("content",""))
            live=r.status==200 and "ARBM_VERCEL_PASS" in text
    except urllib.error.HTTPError as e:
        print(json.dumps({**base,"status":"HTTP_ERROR","http":e.code,"certified_tokens_per_day":0},separators=(",",":"))); return 0
    except Exception as e:
        print(json.dumps({**base,"status":"TRANSPORT_ERROR","error":type(e).__name__,"certified_tokens_per_day":0},separators=(",",":"))); return 0
    account=account_proof(); docs=docs_proof(); ok=live and account and docs
    out={**base,"status":"PASS_ACCOUNT_BOUND" if ok else "LIVE_UNCERTIFIED","http":200,"account_verified":account,"recurring_free":docs,"reset_verified":docs,"no_paid_fallback":True,"docs_verified":docs,"certified_tokens_per_day":CERTIFIED_TPD if ok else 0}
    print(json.dumps(out,separators=(",",":"))); return 0

if __name__=="__main__": raise SystemExit(main())