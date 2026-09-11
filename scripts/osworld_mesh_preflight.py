import base64, json, os, urllib.request

API = "https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v6"
EXPECTED_PIPELINE = "arbm-osworld-v31"
EXPECTED_BUILD = "arbm-osworld-v31-20260911-b"
EXPECTED_EZBR_SHA256 = "35367e7907dd3700ee13176ebb1ec02eccf05d52c52989db748bbb34d6d0f1f7"
PNG_1X1 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nS8AAAAASUVORK5CYII="


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
    "screenshot_data_url": "data:image/png;base64," + PNG_1X1,
    "visual_context": "Synthetic valid PNG plus focused accessibility button for multimodal route proof.",
    "previous_command": "", "executed_count": 0,
    "memory": "", "phase": "plan", "no_progress_count": 0, "step": 1,
    "provider_hint": "groq", "require_multimodal": True,
}
req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST",
    headers={"Authorization": "Bearer " + oidc(), "Content-Type": "application/json"})
with urllib.request.urlopen(req, timeout=75) as response:
    assert response.status == 200
    data = json.loads(response.read())
print(json.dumps(data, separators=(",", ":")))
assert data.get("ok") is True and data.get("status") == "PASS"
assert data.get("pipeline") == EXPECTED_PIPELINE
assert data.get("agent_build") == EXPECTED_BUILD
assert data.get("mandatory_cost_usd") == 0 and data.get("paid_fallback_used") is False
assert data.get("provider") == "groqcloud-free", data.get("provider")
attempts = data.get("provider_attempts") or []
assert any(a.get("route") == "groq-multimodal-free" and a.get("free_plan_proven") is True for a in attempts), attempts
action = data.get("action") or {}
assert action.get("action") == "exec" and "pyautogui." in str(action.get("command") or "")
safe = {
    "status": data.get("status"), "pipeline": data.get("pipeline"), "agent_build": data.get("agent_build"),
    "expected_supabase_ezbr_sha256": EXPECTED_EZBR_SHA256,
    "provider": data.get("provider"), "model": data.get("model"),
    "mandatory_cost_usd": data.get("mandatory_cost_usd"), "paid_fallback_used": data.get("paid_fallback_used"),
    "action": action,
    "provider_attempts": [{k: a.get(k) for k in ("route", "model", "status", "parsed", "free_plan_proven", "reason")}
                          for a in attempts],
}
with open("osworld-mesh-preflight.json", "w", encoding="utf-8") as f:
    json.dump(safe, f, indent=2)
print(json.dumps(safe, separators=(",", ":")))