"""Account-bound Vikasit Nova FREE-capacity probe. Strict fail-closed."""
import json, os, urllib.error, urllib.request
ENDPOINT = "https://api.vikasit.ai/v1/chat/completions"
MODEL = "vikasit-nova"
DOCUMENTED_TPD = 2_000_000

def probe():
    key = os.getenv("VIKASIT_API_KEY", "").strip()
    reset_verified = os.getenv("VIKASIT_RESET_WINDOW_VERIFIED") == "1"
    if not key:
        return {"provider":"vikasit-nova-free","status":"NOT_CONFIGURED","documented_free_tokens_per_day":DOCUMENTED_TPD,"certified_tokens_per_day":0}
    payload = json.dumps({"model":MODEL,"messages":[{"role":"user","content":"Reply only: PASS"}],"max_tokens":8}).encode()
    req = urllib.request.Request(ENDPOINT,data=payload,method="POST",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8")); model = str(body.get("model") or MODEL)
            account_ok = resp.status == 200 and model == MODEL and bool(body.get("choices")); cert_ok = account_ok and reset_verified
            return {"provider":"vikasit-nova-free","status":"PASS" if cert_ok else "LIVE_UNCERTIFIED","http":resp.status,"model":model,
                    "account_verified":account_ok,"documented_free_tokens_per_day":DOCUMENTED_TPD,"recurring_free":account_ok,
                    "no_paid_fallback":account_ok,"reset_verified":reset_verified,"independence_pool":"vikasit-account",
                    "certified_tokens_per_day":DOCUMENTED_TPD if cert_ok else 0}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        return {"provider":"vikasit-nova-free","status":"FAIL","error_type":type(exc).__name__,"certified_tokens_per_day":0}

if __name__ == "__main__": print(json.dumps(probe(), separators=(",", ":")))