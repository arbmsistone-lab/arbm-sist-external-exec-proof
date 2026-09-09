"""Probe Groq model-specific FREE buckets without executing model output."""
import json, os, urllib.error, urllib.request
from account_capacity_probe import API, oidc
MODELS=("qwen/qwen3.6-27b","qwen/qwen3.8-27b","openai/gpt-oss-20b","openai/gpt-oss-120b")
SAFE=("route","model","status","parsed","usage_tokens","free_plan_proven",
      "rate_limit_rpd","rate_limit_tpm","remaining_requests","remaining_tokens",
      "rate_limit_headers","mandatory_cost_usd","paid_fallback_used")

def probe(token, model):
    body={"instruction":"Return one safe inspection command as JSON.",
          "observation":"Groq account-bound model bucket probe. No commands executed.",
          "step":1,"provider_hint":"groq","model_hint":model}
    req=urllib.request.Request(API,data=json.dumps(body).encode(),method="POST",
        headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=45) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:return e.code,json.loads(e.read())
        except Exception:return e.code,{"status":"INVALID_RESPONSE"}
def main():
    if os.environ.get("ZERO_SPEND_MODE")!="HARD": raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    token=oidc(); rows=[]
    for model in MODELS:
        http,data=probe(token,model)
        attempts=[{k:a[k] for k in SAFE if k in a} for a in data.get("provider_attempts",[])]
        rows.append({"model":model,"http":http,"status":data.get("status"),"attempts":attempts})
    print(json.dumps({"provider":"groq","models":rows},separators=(",",":")))

if __name__=="__main__": main()
