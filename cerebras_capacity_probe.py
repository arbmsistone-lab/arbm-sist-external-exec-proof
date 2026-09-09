"""Fail-closed Cerebras FREE capacity probe. Never prints secrets."""
import json, os, urllib.error, urllib.request

API = "https://api.cerebras.ai/v1/chat/completions"
MODEL = "gpt-oss-120b"
SAFE_HEADERS = (
    "x-ratelimit-limit-tokens-day",
    "x-ratelimit-remaining-tokens-day",
    "x-ratelimit-reset-tokens-day",
    "x-ratelimit-limit-tokens-minute",
    "x-ratelimit-remaining-tokens-minute",
    "retry-after",
)

def sanitize_headers(headers):
    return {k.lower(): v for k, v in headers.items() if k.lower() in SAFE_HEADERS}

def main():
    if os.environ.get("ZERO_SPEND_MODE") != "HARD":
        raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    key = os.environ.get("CEREBRAS_API_KEY", "").strip()
    if not key:
        print(json.dumps({"provider":"cerebras","status":"NOT_CONFIGURED","certified_tokens_per_day":0}))
        return 0
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role":"user","content":"Reply only ARBM_CEREBRAS_PASS"}],
        "max_tokens": 16,
        "temperature": 0,
    }).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Authorization": "Bearer " + key,
        "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = json.loads(r.read())
            text = str(raw.get("choices", [{}])[0].get("message", {}).get("content", ""))
            ok = r.status == 200 and "ARBM_CEREBRAS_PASS" in text
            print(json.dumps({
                "provider":"cerebras","status":"PASS" if ok else "INVALID_RESPONSE",
                "http":r.status,"model":MODEL,"headers":sanitize_headers(r.headers),
                "mandatory_cost_usd":0,"paid_fallback_used":False,
                "certified_tokens_per_day":0,
            }, separators=(",",":")))
            return 0 if ok else 2
    except urllib.error.HTTPError as e:
        print(json.dumps({"provider":"cerebras","status":"HTTP_ERROR","http":e.code,
                          "headers":sanitize_headers(e.headers),"certified_tokens_per_day":0}))
        return 2
    except Exception as e:
        print(json.dumps({"provider":"cerebras","status":"TRANSPORT_ERROR",
                          "error":type(e).__name__,"certified_tokens_per_day":0}))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
