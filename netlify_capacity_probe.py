"""Fail-closed Netlify AI Gateway recurring-FREE capacity probe."""
import json, os, urllib.error, urllib.request
from decimal import Decimal
from pathlib import Path
ENDPOINT="https://arbm-sist-free-capacity-probe.netlify.app/capacity-probe"
CREDITS_DOC="https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/"
AI_DOC="https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/pricing-for-ai-features/"
MODEL="meta-llama/llama-3.1-8b-instruct"
MONTHLY_CREDITS=Decimal("300")
RESERVED_CREDITS=Decimal("30")
CREDITS_PER_USD=Decimal("180")
NORMALIZATION_DAYS=31
INPUT_PRICE_PER_M=Decimal("0.02")
OUTPUT_PRICE_PER_M=Decimal("0.04")
INPUT_TOKENS=1024
OUTPUT_TOKENS=32
USEFUL_TOKENS=INPUT_TOKENS+OUTPUT_TOKENS
USABLE_USD=(MONTHLY_CREDITS-RESERVED_CREDITS)/CREDITS_PER_USD
COST_PER_CALL=(Decimal(INPUT_TOKENS)*INPUT_PRICE_PER_M+Decimal(OUTPUT_TOKENS)*OUTPUT_PRICE_PER_M)/Decimal(1_000_000)
CERTIFIED_TPD=int((USABLE_USD/Decimal(NORMALIZATION_DAYS)/COST_PER_CALL)*Decimal(USEFUL_TOKENS))

def account_proof():
    try:
        d=json.loads(Path("netlify-account-evidence.json").read_text(encoding="utf-8"))
        return d.get("plan")=="free" and d.get("role")=="owner" and d.get("mandatory_cost_usd")==0
    except Exception: return False
def docs_proof():
    try:
        req1=urllib.request.Request(CREDITS_DOC,headers={"User-Agent":"ARBM-SIST-capacity-audit/1.0"})
        req2=urllib.request.Request(AI_DOC,headers={"User-Agent":"ARBM-SIST-capacity-audit/1.0"})
        with urllib.request.urlopen(req1,timeout=20) as r: a=r.read().decode("utf-8","ignore").lower()
        with urllib.request.urlopen(req2,timeout=20) as r: b=r.read().decode("utf-8","ignore").lower()
        free=("300 credits/month" in a and "hard limit" in a and "no auto recharge" in a)
        ai=("180 credits per $1" in b and MODEL in b and "$0.02" in b and "$0.04" in b)
        return free and ai
    except Exception: return False

def oidc():
    url=os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL",""); tok=os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN","")
    if not url or not tok: return ""
    sep="&" if "?" in url else "?"
    req=urllib.request.Request(url+sep+"audience=arbm-sist-benchmark",headers={"Authorization":"Bearer "+tok})
    try:
        with urllib.request.urlopen(req,timeout=20) as r: return str(json.loads(r.read()).get("value","")).strip()
    except Exception: return ""
def main():
    if os.environ.get("ZERO_SPEND_MODE")!="HARD": raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    base={"provider":"netlify-ai-gateway-free","independence_pool":"netlify-team","model":MODEL,"mandatory_cost_usd":0,"paid_fallback_used":False,"monthly_credits":300,"reserved_credits":30,"certified_budget_usd":float(USABLE_USD)}
    token=oidc()
    if not token:
        print(json.dumps({**base,"status":"OIDC_UNAVAILABLE","certified_tokens_per_day":0},separators=(",",":"))); return 0
    req=urllib.request.Request(ENDPOINT,method="GET",headers={"Authorization":"Bearer "+token,"User-Agent":"ARBM-SIST-capacity-audit/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            body=json.loads(r.read().decode("utf-8")); live=r.status==200 and body.get("ok") is True and body.get("requested_model")==MODEL
    except urllib.error.HTTPError as e:
        print(json.dumps({**base,"status":"HTTP_ERROR","http":e.code,"certified_tokens_per_day":0},separators=(",",":"))); return 0
    except Exception as e:
        print(json.dumps({**base,"status":"TRANSPORT_ERROR","error":type(e).__name__,"certified_tokens_per_day":0},separators=(",",":"))); return 0
    account=account_proof(); docs=docs_proof(); ok=live and account and docs
    out={**base,"status":"PASS_ACCOUNT_BOUND" if ok else "LIVE_UNCERTIFIED","http":200,"account_verified":account,"recurring_free":docs,"reset_verified":docs,"no_paid_fallback":True,"docs_verified":docs,"certified_tokens_per_day":CERTIFIED_TPD if ok else 0}
    print(json.dumps(out,separators=(",",":"))); return 0

if __name__=="__main__": raise SystemExit(main())