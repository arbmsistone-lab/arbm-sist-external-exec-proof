"""Real, fail-closed Mistral FREE probe. Never executes returned commands."""
import json
import os
import urllib.error
import urllib.request

API = "https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v7"
MODELS = ("ministral-3b-latest", "ministral-8b-latest", "mistral-small-latest")


def oidc():
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    token = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    separator = "&" if "?" in url else "?"
    request = urllib.request.Request(url + separator + "audience=arbm-sist-benchmark",
                                     headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read())["value"]


def live_proven(http, data):
    attempts = data.get("provider_attempts") or []
    return (http == 200 and data.get("ok") is True and data.get("status") == "PASS"
            and data.get("provider") == "mistral-free"
            and type(data.get("mandatory_cost_usd")) in (int, float)
            and data["mandatory_cost_usd"] == 0 and data.get("paid_fallback_used") is False
            and any(a.get("route") == "mistral-free" and a.get("status") == 200
                    and a.get("parsed") is True for a in attempts)
            and all(a.get("route") in ("mistral", "mistral-free") for a in attempts))


def model_unavailable(data):
    attempts = data.get("provider_attempts") or []
    if len(attempts) != 1:
        return False
    attempt = attempts[0]
    message = str(attempt.get("error_message", "")).lower()
    return (attempt.get("route") == "mistral-free" and attempt.get("status") in (400, 404, 422)
            and "model" in message and any(word in message for word in
                ("not found", "does not exist", "unavailable", "not available", "unsupported", "invalid model")))


def request_probe(token, model):
    body = {"instruction": "Return one safe inspection command as JSON.",
            "observation": "No commands executed yet.", "step": 1,
            "provider_hint": "mistral", "model_hint": model}
    request = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        try:
            return error.code, json.loads(error.read())
        except (ValueError, UnicodeError):
            return error.code, {"status": "INVALID_RESPONSE"}
    except (urllib.error.URLError, TimeoutError, ValueError):
        return None, {"status": "TRANSPORT_OR_INVALID_RESPONSE"}


def main():
    if os.environ.get("ZERO_SPEND_MODE") != "HARD":
        print(json.dumps({"live_proven": False, "status": "ZERO_SPEND_HARD_REQUIRED"}))
        return 2
    token = oidc()
    for model in MODELS:
        http, data = request_probe(token, model)
        safe_fields = ("route", "model", "status", "parsed", "usage_tokens", "usage",
                       "retry_after", "rate_limit_headers", "mandatory_cost_usd", "paid_fallback_used")
        output = {"http": http, "ok": data.get("ok"), "status": data.get("status"),
                  "provider": data.get("provider"), "model": data.get("model"), "requested_model": model,
                  "mandatory_cost_usd": data.get("mandatory_cost_usd"),
                  "paid_fallback_used": data.get("paid_fallback_used"),
                  "provider_attempts": [{k: a[k] for k in safe_fields if k in a}
                                        for a in data.get("provider_attempts", [])],
                  "model_unavailable": model_unavailable(data), "live_proven": live_proven(http, data)}
        print(json.dumps(output, separators=(",", ":")), flush=True)
        if output["live_proven"]:
            return 0
        if not output["model_unavailable"]:
            break
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
