import json, os, urllib.request

API = "https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v7"

def oidc():
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    token = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(url + sep + "audience=arbm-sist-benchmark",
                                 headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())["value"]

body = {
    "instruction": "Activate the currently focused OK button using the keyboard.",
    "observation": "[button] name='OK' position (100,100) size (120,40) focused true",
    "previous_command": "",
    "step": 1,
}
req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST",
    headers={"Authorization": "Bearer " + oidc(), "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=70) as response:
    assert response.status == 200
    data = json.loads(response.read())
assert data.get("ok") is True and data.get("status") == "PASS"
assert data.get("pipeline") == "osworld-free-mesh-v1"
assert data.get("mandatory_cost_usd") == 0
assert data.get("paid_fallback_used") is False
action = data.get("action") or {}
assert action.get("action") == "exec"
assert "pyautogui." in str(action.get("command") or "")
safe = {
    "status": data.get("status"), "pipeline": data.get("pipeline"),
    "provider": data.get("provider"), "model": data.get("model"),
    "mandatory_cost_usd": data.get("mandatory_cost_usd"),
    "paid_fallback_used": data.get("paid_fallback_used"),
    "action": action,
    "provider_attempts": [{k: a.get(k) for k in ("route", "model", "status", "parsed", "reason")}
                          for a in data.get("provider_attempts", [])],
}
with open("osworld-mesh-preflight.json", "w", encoding="utf-8") as f:
    json.dump(safe, f, indent=2)
print(json.dumps(safe, separators=(",", ":")))
