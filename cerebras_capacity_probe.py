"""Fail-closed Cerebras FREE capacity probe. Never prints secrets."""
import json, os, urllib.error, urllib.request

API = "https://api.cerebras.ai/v1/chat/completions"
MODELS = {
    "gpt-oss-120b": {"documented_tpd": 1_000_000, "free_rpd": 14_400},
    "zai-glm-4.7": {"documented_tpd": 1_000_000, "free_rpd": 100},
}
SAFE_HEADERS = (
    "x-ratelimit-limit-requests-day", "x-ratelimit-remaining-requests-day",
    "x-ratelimit-reset-requests-day", "x-ratelimit-limit-tokens-day",
    "x-ratelimit-remaining-tokens-day", "x-ratelimit-reset-tokens-day",
    "x-ratelimit-limit-tokens-minute", "x-ratelimit-remaining-tokens-minute",
    "retry-after",
)

def sanitize_headers(headers):
    return {k.lower(): v for k, v in headers.items() if k.lower() in SAFE_HEADERS}

def _int_header(headers, name):
    try: return int(str(headers.get(name, "")).replace(",", ""))
    except ValueError: return None

def probe_model(key, model, spec):
    body = json.dumps({
        "model": model,
        "messages": [{"role":"user","content":"Reply only ARBM_CEREBRAS_PASS"}],
        "max_tokens": 16, "temperature": 0,
    }).encode()
    req = urllib.request.Request(API, data=body, method="POST", headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = json.loads(r.read())
            text = str(raw.get("choices", [{}])[0].get("message", {}).get("content", ""))
            headers = sanitize_headers(r.headers)
            rpd = _int_header(headers, "x-ratelimit-limit-requests-day")
            account_free = r.status == 200 and rpd == spec["free_rpd"]
            valid = account_free and "ARBM_CEREBRAS_PASS" in text
            return {"model":model,"http":r.status,"headers":headers,
                    "free_tier_proven":account_free,"valid":valid,
                    "certified_tokens_per_day":spec["documented_tpd"] if valid else 0}
    except urllib.error.HTTPError as e:
        return {"model":model,"http":e.code,"headers":sanitize_headers(e.headers),
                "free_tier_proven":False,"valid":False,"certified_tokens_per_day":0}
    except Exception as e:
        return {"model":model,"status":"TRANSPORT_ERROR","error":type(e).__name__,
                "free_tier_proven":False,"valid":False,"certified_tokens_per_day":0}

def main():
    if os.environ.get("ZERO_SPEND_MODE") != "HARD":
        raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    key = os.environ.get("CEREBRAS_API_KEY", "").strip()
    if not key:
        print(json.dumps({"provider":"cerebras","status":"NOT_CONFIGURED",
                          "certified_tokens_per_day":0}, separators=(",",":")))
        return 0
    rows = [probe_model(key, model, spec) for model, spec in MODELS.items()]
    all_free = all(row["valid"] for row in rows)
    certified = sum(row["certified_tokens_per_day"] for row in rows) if all_free else 0
    print(json.dumps({
        "provider":"cerebras","status":"PASS" if all_free else "LIVE_UNCERTIFIED",
        "independence_pool":"cerebras-organization","account_verified":all_free,
        "recurring_free":all_free,"no_paid_fallback":all_free,
        "mandatory_cost_usd":0,"paid_fallback_used":False,
        "model_buckets":rows,"certified_tokens_per_day":certified,
    }, separators=(",",":")))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
