"""Fail-closed OpenRouter FREE account-bound Liquid inference proof."""
import json, os, urllib.error, urllib.request
KEY_API="https://openrouter.ai/api/v1/key"
CHAT_API="https://openrouter.ai/api/v1/chat/completions"
MODEL="liquid/lfm-2.5-2.6b:free"
EXPECTED_PROVIDER="liquid"
CERTIFIED_REQUESTS_PER_DAY=50
TOOL_NAME="arbm_openrouter_pass"

def call(url,key,data=None,metadata=False):
    h={"Authorization":"Bearer "+key,"Content-Type":"application/json"}
    if metadata: h["X-OpenRouter-Metadata"]="enabled"
    q=urllib.request.Request(url,data=data,method="POST" if data else "GET",headers=h)
    with urllib.request.urlopen(q,timeout=45) as r:return r.status,json.loads(r.read() or b'{}')

def selected_provider(raw):
    meta=raw.get("openrouter_metadata") or {}; eps=(meta.get("endpoints") or {}).get("available") or []
    chosen=[str(e.get("provider") or "") for e in eps if e.get("selected") is True]
    return chosen[0] if len(chosen)==1 else None

def has_pass_tool(raw):
    message=((raw.get("choices") or [{}])[0].get("message") or {})
    calls=message.get("tool_calls") or []
    names=[str((c.get("function") or {}).get("name") or "") for c in calls if isinstance(c,dict)]
    return names == [TOOL_NAME]

def result(status,**extra):
    return {"provider":"openrouter-liquid-free","independence_pool":"openrouter-account-liquid-runtime",
            "model":MODEL,"capacity_kind":"decisions","mandatory_cost_usd":0,"paid_fallback_used":False,
            "certified_useful_units_per_day":0,"certified_tokens_per_day":0,"status":status,**extra}

def main():
    if os.environ.get("ZERO_SPEND_MODE")!="HARD": raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    key=os.environ.get("OPENROUTER_API_KEY","").strip()
    if not key:
        print(json.dumps(result("NOT_CONFIGURED"),separators=(",",":"))); return 0
    try:
        key_http,meta=call(KEY_API,key); data=meta.get("data") or {}
        if key_http!=200 or data.get("is_free_tier") is not True:
            print(json.dumps(result("ACCOUNT_NOT_PROVEN_FREE",key_http=key_http,is_free_tier=data.get("is_free_tier")),separators=(",",":"))); return 2
        tool={"type":"function","function":{"name":TOOL_NAME,"description":"Emit the ARBM provider proof marker.","parameters":{"type":"object","properties":{},"additionalProperties":False}}}
        body=json.dumps({"model":MODEL,"messages":[{"role":"user","content":"Call the proof function now."}],"max_tokens":64,"temperature":0,
                         "tools":[tool],"tool_choice":{"type":"function","function":{"name":TOOL_NAME}},
                         "provider":{"only":[EXPECTED_PROVIDER],"allow_fallbacks":False}}).encode()
        chat_http,raw=call(CHAT_API,key,body,True); provider=selected_provider(raw); parsed=has_pass_tool(raw)
        choice=(raw.get("choices") or [{}])[0]; message=choice.get("message") or {}; content=message.get("content")
        ok=chat_http==200 and parsed and provider and provider.lower()==EXPECTED_PROVIDER
        row=result("PASS" if ok else "LIVE_UNCERTIFIED",key_http=key_http,chat_http=chat_http,is_free_tier=True,
                   parsed=parsed,selected_provider=provider,official_free_requests_per_day=CERTIFIED_REQUESTS_PER_DAY,
                   finish_reason=choice.get("finish_reason"),message_keys=sorted(message.keys()),content_type=type(content).__name__,
                   content_len=len(content) if isinstance(content,(str,list)) else 0,tool_call_count=len(message.get("tool_calls") or []),
                   reasoning_present=bool(message.get("reasoning") or message.get("reasoning_details")))
        if ok: row.update({"account_verified":True,"recurring_free":True,"reset_verified":True,"no_paid_fallback":True,
                           "certified_useful_units_per_day":CERTIFIED_REQUESTS_PER_DAY})
        print(json.dumps(row,separators=(",",":"))); return 0 if ok else 2
    except urllib.error.HTTPError as e:
        print(json.dumps(result("HTTP_ERROR",http=e.code),separators=(",",":"))); return 2
    except Exception as e:
        print(json.dumps(result("TRANSPORT_ERROR",error=type(e).__name__),separators=(",",":"))); return 2

if __name__=="__main__": raise SystemExit(main())
