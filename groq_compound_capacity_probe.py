"""Account-bound Groq Compound capacity probe. Never executes model output."""
import json, os, urllib.error, urllib.request
API="https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v7"
MODELS=("groq/compound","groq/compound-mini")
SAFE=("route","model","status","parsed","usage_tokens","prompt_tokens",
      "completion_tokens","free_plan_proven","rate_limit_rpd","rate_limit_tpm",
      "remaining_requests","remaining_tokens","rate_limit_headers",
      "mandatory_cost_usd","paid_fallback_used","error_message")

def oidc():
    url=os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    tok=os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    sep="&" if "?" in url else "?"
    req=urllib.request.Request(url+sep+"audience=arbm-sist-benchmark",
        headers={"Authorization":"Bearer "+tok})
    with urllib.request.urlopen(req,timeout=20) as r:
        return json.loads(r.read())["value"]
def probe(token,model):
    block=("classify route score extract decide short json safe capacity audit "*500)
    body={"instruction":block[:15000],"observation":block[:15000],"step":1,
          "provider_hint":"groq","model_hint":model}
    req=urllib.request.Request(API,data=json.dumps(body).encode(),method="POST",
        headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=60) as r:
            return r.status,json.loads(r.read())
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
    print(json.dumps({"provider":"groq-compound","models":rows},separators=(",",":")))
if __name__=="__main__": main()
