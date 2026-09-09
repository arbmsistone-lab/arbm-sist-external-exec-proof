"""Fail-closed SambaNova multi-model FREE-capacity probe."""
import json, os, urllib.error, urllib.request
API="https://api.sambanova.ai/v1/chat/completions"
MODELS=("Meta-Llama-3.3-70B-Instruct","gpt-oss-120b")
TPD_PER_MODEL=200_000
SAFE_HEADERS=("x-ratelimit-limit-requests","x-ratelimit-remaining-requests","x-ratelimit-reset-requests","x-ratelimit-limit-requests-day","x-ratelimit-remaining-requests-day","x-ratelimit-reset-requests-day","x-ratelimit-limit-tokens-day","x-ratelimit-remaining-tokens-day","x-ratelimit-reset-tokens-day","retry-after")

def sanitize(headers):
    return {k.lower():str(v)[:120] for k,v in headers.items() if k.lower() in SAFE_HEADERS}

def call(key, model):
    body=json.dumps({"model":model,"messages":[{"role":"user","content":"Reply only ARBM_SAMBANOVA_PASS"}],"max_tokens":16,"temperature":0}).encode()
    req=urllib.request.Request(API,data=body,method="POST",headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=30) as r:
        raw=json.loads(r.read()); text=str(raw.get("choices",[{}])[0].get("message",{}).get("content","")); headers=sanitize(r.headers)
        live=r.status==200 and "ARBM_SAMBANOVA_PASS" in text
        account=live and headers.get("x-ratelimit-limit-tokens-day")==str(TPD_PER_MODEL)
        return {"model":model,"http":r.status,"live":live,"account_bound":account,"headers":headers}

def main():
    if os.environ.get("ZERO_SPEND_MODE")!="HARD": raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    key=os.environ.get("SAMBANOVA_API_KEY","").strip()
    base={"provider":"sambanova-free","independence_pool":"sambanova-account","documented_free_tokens_per_model_day":TPD_PER_MODEL,"mandatory_cost_usd":0,"paid_fallback_used":False}
    if not key:
        print(json.dumps({**base,"status":"NOT_CONFIGURED","certified_tokens_per_day":0},separators=(",",":"))); return 0
    rows=[]
    try:
        for model in MODELS: rows.append(call(key,model))
    except urllib.error.HTTPError as e:
        print(json.dumps({**base,"status":"HTTP_ERROR","http":e.code,"certified_tokens_per_day":0},separators=(",",":"))); return 2
    except Exception as e:
        print(json.dumps({**base,"status":"TRANSPORT_ERROR","error":type(e).__name__,"certified_tokens_per_day":0},separators=(",",":"))); return 2
    proven=[r for r in rows if r["account_bound"]]
    certified=len(proven)*TPD_PER_MODEL
    status="PASS_ACCOUNT_BOUND" if certified==len(MODELS)*TPD_PER_MODEL else ("PARTIAL_ACCOUNT_BOUND" if certified else "PASS_UNCERTIFIED")
    print(json.dumps({**base,"status":status,"models":rows,"account_verified":bool(proven),"recurring_free":bool(proven),"reset_verified":bool(proven),"no_paid_fallback":bool(proven),"certified_tokens_per_day":certified},separators=(",",":")))
    return 0 if all(r["live"] for r in rows) else 2

if __name__=="__main__":
    raise SystemExit(main())
