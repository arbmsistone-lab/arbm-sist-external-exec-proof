"""Account-bound FREE capacity probe; never executes model output."""
import argparse, json, os, urllib.error, urllib.request
API="https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v7"
PROVIDERS=("groq","google","lightning","cloudflare","mistral")
SAFE=("route","model","status","parsed","usage_tokens","usage","retry_after",
      "rate_limit_headers","rate_limit_remaining","error_message","free_plan_proven",
      "rate_limit_rpd","rate_limit_tpm","remaining_requests","remaining_tokens",
      "quota_limit","quota_metric","mandatory_cost_usd","paid_fallback_used")
def oidc():
    url=os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    tok=os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    sep="&" if "?" in url else "?"
    req=urllib.request.Request(url+sep+"audience=arbm-sist-benchmark",
        headers={"Authorization":"Bearer "+tok})
    with urllib.request.urlopen(req,timeout=20) as r:return json.loads(r.read())["value"]
def probe(token,provider):
    body={"instruction":"Return one safe inspection command as JSON.",
          "observation":"Account capacity evidence probe. No commands executed.",
          "step":1,"provider_hint":provider, **({"model_hint":"@cf/meta/llama-3.2-1b-instruct"} if provider=="cloudflare" else {})}
    req=urllib.request.Request(API,data=json.dumps(body).encode(),method="POST",
        headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=45) as r:return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:return e.code,json.loads(e.read())
        except Exception:return e.code,{"status":"INVALID_RESPONSE"}
    except Exception:return None,{"status":"TRANSPORT_OR_INVALID_RESPONSE"}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--require-certified",action="store_true"); args=ap.parse_args()
    if os.environ.get("ZERO_SPEND_MODE")!="HARD":raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    token=oidc(); certified_ok={"groq":False,"lightning":False,"cloudflare":False}
    for provider in PROVIDERS:
        http,data=probe(token,provider)
        out={"provider_hint":provider,"http":http,"status":data.get("status"),
             "provider":data.get("provider"),"mandatory_cost_usd":data.get("mandatory_cost_usd"),
             "paid_fallback_used":data.get("paid_fallback_used"),
             "provider_attempts":[{k:a[k] for k in SAFE if k in a}
                                  for a in data.get("provider_attempts",[])]}
        print(json.dumps(out,separators=(",",":")),flush=True)
        aliases={"groq":{"groq","groq-json-object","groq-json-text"},"lightning":{"lightning","lightning-free"},"cloudflare":{"cloudflare"}}
        if provider in certified_ok:
            certified_ok[provider]=(http==200 and data.get("mandatory_cost_usd",0)==0 and data.get("paid_fallback_used",False) is False and any(a.get("route") in aliases[provider] and a.get("status")==200 and a.get("parsed") is True and a.get("mandatory_cost_usd",0)==0 and a.get("paid_fallback_used",False) is False for a in data.get("provider_attempts",[])))
    if args.require_certified and not all(certified_ok.values()): raise SystemExit(2)
if __name__=="__main__":main()
