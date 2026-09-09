"""Fail-closed SambaNova FREE capacity probe. Never prints secrets."""
import json, os, urllib.error, urllib.request

API = "https://api.sambanova.ai/v1/chat/completions"
MODEL = "Meta-Llama-3.3-70B-Instruct"
DOCUMENTED_FREE_TPD = 200_000
SAFE_HEADERS = (
    "x-ratelimit-limit-requests",
    "x-ratelimit-remaining-requests",
    "x-ratelimit-reset-requests",
    "x-ratelimit-limit-requests-day",
    "x-ratelimit-remaining-requests-day",
    "x-ratelimit-reset-requests-day",
    "x-ratelimit-limit-tokens-day",
    "x-ratelimit-remaining-tokens-day",
    "x-ratelimit-reset-tokens-day",
    "retry-after",
)

def sanitize_headers(headers):
    return {k.lower(): str(v)[:120] for k, v in headers.items()
            if k.lower() in SAFE_HEADERS}

def result(status, **extra):
    return {"provider":"sambanova-free","status":status,
            "documented_free_tokens_per_day":DOCUMENTED_FREE_TPD,
            "certified_tokens_per_day":0, **extra}

def main():
    if os.environ.get("ZERO_SPEND_MODE") != "HARD":
        raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    key = os.environ.get("SAMBANOVA_API_KEY", "").strip()
    if not key:
        print(json.dumps(result("NOT_CONFIGURED"), separators=(",",":")))
        return 0
    body = json.dumps({"model":MODEL,"messages":[{"role":"user","content":"Reply only ARBM_SAMBANOVA_PASS"}],"max_tokens":16,"temperature":0}).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw=json.loads(r.read()); text=str(raw.get("choices",[{}])[0].get("message",{}).get("content",""))
            headers=sanitize_headers(r.headers); live_ok=r.status==200 and "ARBM_SAMBANOVA_PASS" in text
            daily=headers.get("x-ratelimit-limit-tokens-day")
            account_ok=live_ok and daily==str(DOCUMENTED_FREE_TPD)
            out=result("PASS_ACCOUNT_BOUND" if account_ok else "PASS_UNCERTIFIED",http=r.status,model=MODEL,headers=headers,mandatory_cost_usd=0,paid_fallback_used=False)
            if account_ok: out["certified_tokens_per_day"]=DOCUMENTED_FREE_TPD
            print(json.dumps(out,separators=(",",":"))); return 0 if live_ok else 2
    except urllib.error.HTTPError as e:
        print(json.dumps(result("HTTP_ERROR",http=e.code,headers=sanitize_headers(e.headers)),separators=(",",":"))); return 2
    except Exception as e:
        print(json.dumps(result("TRANSPORT_ERROR",error=type(e).__name__),separators=(",",":"))); return 2

if __name__ == "__main__":
    raise SystemExit(main())
