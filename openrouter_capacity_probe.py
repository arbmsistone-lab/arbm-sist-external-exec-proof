"""Fail-closed OpenRouter FREE useful-capacity probe."""
import json, os, urllib.error, urllib.request

API="https://openrouter.ai/api/v1/chat/completions"
MODEL="openrouter/free"
MIN_REQUESTS_PER_DAY=50
MIN_USEFUL_INPUT_TOKENS=40_000
CERTIFIED_TPD=MIN_REQUESTS_PER_DAY*MIN_USEFUL_INPUT_TOKENS

SAFE_HEADERS=("x-ratelimit-limit","x-ratelimit-remaining","x-ratelimit-reset","retry-after")

def _safe(headers):
    return {k.lower():v for k,v in headers.items() if k.lower() in SAFE_HEADERS}

def main():
    if os.environ.get("ZERO_SPEND_MODE")!="HARD":
        raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    key=os.environ.get("OPENROUTER_API_KEY","").strip()
    if not key:
        print(json.dumps({"provider":"openrouter","status":"NOT_CONFIGURED","certified_tokens_per_day":0}))
        return 0
    prompt=("ARBM capacity evidence. Return only OK. "+("x "*MIN_USEFUL_INPUT_TOKENS)).strip()
    body=json.dumps({"model":MODEL,"messages":[{"role":"user","content":prompt}],"max_tokens":4,"temperature":0}).encode()
    req=urllib.request.Request(API,data=body,method="POST",headers={
        "Authorization":"Bearer "+key,"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=45) as r:
            raw=json.loads(r.read())
            usage=raw.get("usage") or {}
            prompt_tokens=usage.get("prompt_tokens")
            ok=r.status==200 and type(prompt_tokens) is int and prompt_tokens>=MIN_USEFUL_INPUT_TOKENS
            result={"provider":"openrouter","http":r.status,"model":MODEL,
                    "prompt_tokens":prompt_tokens,"headers":_safe(r.headers),
                    "mandatory_cost_usd":0,"paid_fallback_used":False,
                    "certified_tokens_per_day":CERTIFIED_TPD if ok else 0,
                    "status":"PASS" if ok else "LIVE_UNCERTIFIED"}
            print(json.dumps(result,separators=(",",":")))
            return 0 if ok else 2
    except urllib.error.HTTPError as e:
        print(json.dumps({"provider":"openrouter","status":"HTTP_ERROR","http":e.code,
                          "headers":_safe(e.headers),"certified_tokens_per_day":0}))
        return 2
    except Exception as e:
        print(json.dumps({"provider":"openrouter","status":"TRANSPORT_ERROR",
                          "error":type(e).__name__,"certified_tokens_per_day":0}))
        return 2

if __name__=="__main__":
    raise SystemExit(main())
