"""Account-bound Vikasit Nova FREE-capacity probe. Strict fail-closed."""
import json, os, urllib.error, urllib.request

ENDPOINT = "https://api.vikasit.ai/v1/chat/completions"
MODEL = "vikasit-nova"
# No current official recurring TPD proof is accepted. Keep zero until re-proven.
DOCUMENTED_TPD = 0

def probe():
    key = os.getenv("VIKASIT_API_KEY", "").strip()
    reset_verified = os.getenv("VIKASIT_RESET_WINDOW_VERIFIED") == "1"
    official_tpd_verified = os.getenv("VIKASIT_OFFICIAL_RECURRING_TPD_VERIFIED") == "1"
    base = {"provider":"vikasit-nova-free","documented_free_tokens_per_day":DOCUMENTED_TPD,"mandatory_cost_usd":0,"paid_fallback_used":False,"independence_pool":"vikasit-account"}
    if not key:
        return {**base,"status":"NOT_CONFIGURED","certified_tokens_per_day":0}
    payload = json.dumps({"model":MODEL,"messages":[{"role":"user","content":"Reply only: PASS"}],"max_tokens":8}).encode()
    req = urllib.request.Request(ENDPOINT,data=payload,method="POST",headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8")); model = str(body.get("model") or MODEL)
            account_ok = resp.status == 200 and model == MODEL and bool(body.get("choices"))
            cert_ok = account_ok and reset_verified and official_tpd_verified and DOCUMENTED_TPD > 0
            return {**base,"status":"PASS" if cert_ok else "LIVE_UNCERTIFIED","http":resp.status,"model":model,"account_verified":account_ok,"recurring_free":cert_ok,"no_paid_fallback":account_ok,"reset_verified":reset_verified,"official_tpd_verified":official_tpd_verified,"certified_tokens_per_day":DOCUMENTED_TPD if cert_ok else 0}
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as exc:
        return {**base,"status":"FAIL","error_type":type(exc).__name__,"certified_tokens_per_day":0}

if __name__ == "__main__": print(json.dumps(probe(), separators=(",", ":")))