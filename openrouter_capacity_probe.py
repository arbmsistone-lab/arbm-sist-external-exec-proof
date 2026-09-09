"""Fail-closed OpenRouter FREE account-bound useful-capacity probe."""
import json, os, urllib.error, urllib.request
KEY_API="https://openrouter.ai/api/v1/key"
CHAT_API="https://openrouter.ai/api/v1/chat/completions"
MODEL="openrouter/free"
CERTIFIED_REQUESTS_PER_DAY=50
CAPACITY_KIND="decisions"

def call(url,key,data=None):
    headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"}
    req=urllib.request.Request(url,data=data,method="POST" if data else "GET",headers=headers)
    with urllib.request.urlopen(req,timeout=45) as r:
        return r.status,json.loads(r.read() or b'{}')

def result(status,**extra):
    return {"provider":"openrouter-free","independence_pool":"openrouter-account",
            "model":MODEL,"capacity_kind":CAPACITY_KIND,"mandatory_cost_usd":0,
            "paid_fallback_used":False,"certified_useful_units_per_day":0,
            "certified_tokens_per_day":0,"status":status,**extra}

def main():
    if os.environ.get("ZERO_SPEND_MODE")!="HARD": raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    key=os.environ.get("OPENROUTER_API_KEY","").strip()
    if not key:
        print(json.dumps(result("NOT_CONFIGURED"),separators=(",",":"))); return 0
    try:
        http,meta=call(KEY_API,key); data=meta.get("data") or {}
        free=(http==200 and data.get("is_free_tier") is True)
        if not free:
            print(json.dumps(result("ACCOUNT_NOT_PROVEN_FREE",key_http=http,is_free_tier=data.get("is_free_tier")),separators=(",",":"))); return 2
        body=json.dumps({"model":MODEL,"messages":[{"role":"user","content":"Reply only ARBM_OPENROUTER_PASS"}],"max_tokens":16,"temperature":0}).encode()
        chat_http,raw=call(CHAT_API,key,body)
        parsed=bool((raw.get("choices") or [{}])[0].get("message",{}).get("content"))
        ok=chat_http==200 and parsed
        row=result("PASS" if ok else "LIVE_UNCERTIFIED",key_http=http,chat_http=chat_http,
                   is_free_tier=True,parsed=parsed,official_free_requests_per_day=CERTIFIED_REQUESTS_PER_DAY)
        if ok: row["certified_useful_units_per_day"]=CERTIFIED_REQUESTS_PER_DAY
        print(json.dumps(row,separators=(",",":"))); return 0 if ok else 2
    except urllib.error.HTTPError as e:
        print(json.dumps(result("HTTP_ERROR",http=e.code),separators=(",",":"))); return 2
    except Exception as e:
        print(json.dumps(result("TRANSPORT_ERROR",error=type(e).__name__),separators=(",",":"))); return 2

if __name__=="__main__": raise SystemExit(main())
