import base64, json, os, time, urllib.request, urllib.error

API = "https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v5"
EXPECTED_PIPELINE = "arbm-osworld-v31-isolated"
EXPECTED_BUILD = "arbm-osworld-v31e-isolated-20260911"
EXPECTED_EZBR_SHA256 = "85ac465da11e07b0f54139c568f05f5b44db20bde592f6118f397f39067a7289"
PNG_1X1 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAABe0lEQVR42u3asa6CMBQGYFB3nPsIOhhk0XSE93D0eRxITIghLD6DBlZhIOnIC7C44WJqWM4dSDopJhfQmvz/RAtDv3AawklNIjJ+OSPjxwMAAAAA8N1MXt0wTVO3tT79ZKGEtC2h9hf3ybQXM0oIAAAAAAAAAAAAAAAAvgYIw9BxnPV67ThOFEXN5HQ6bS7KsrRt+3q9Dvuj+TRvHyCi0+nEOa+qioiqquKcx3FMRJZlEZGUknOeZRl1S/tKOgFc103TVA0vl4vneQqw2WyCIKDOGRDAGJNSqqGUkjHWAHa73Xa7pT7SvpJRv9XY/L/Wde37/rCl38smns1mQgg1FELM53PDMMbjcZ7n9/t9v99/olv07xI6n8+c89vtpjZxkiRqD5RlyRgrikLfPUBEh8PBtu3VarVcLsMwbCYbABEdj8fFYvF4PIYDmK/aPqobo09fCK1FAAAAAAAAAAAAAAAAAAAArfL+qIGGx1ZQQjrFxMFXAAAAAIAu+QMm7VscSt4QYQAAAABJRU5ErkJggg=="


def oidc():
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    token = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(url + sep + "audience=arbm-sist-benchmark",
                                 headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())["value"]


body = {
    "instruction": "Return action exactly exec and command exactly pyautogui.press('enter') to activate the currently focused OK button. Do not use any other action value.",
    "observation": "[button] name='OK' position (100,100) size (120,40) focused true",
    "screenshot_data_url": "data:image/png;base64," + PNG_1X1,
    "visual_context": "Synthetic valid PNG plus focused accessibility button for multimodal route proof.",
    "previous_command": "", "executed_count": 0,
    "memory": "", "phase": "plan", "no_progress_count": 0, "step": 1,
    "provider_hint": "groq", "require_multimodal": True,
}
status, data = None, {}
for attempt_no in range(1, 16):
    req = urllib.request.Request(API, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + oidc(), "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=75) as response:
            status = response.status
            data = json.loads(response.read())
    except urllib.error.HTTPError as err:
        status = err.code
        data = json.loads(err.read())
    print(json.dumps({"attempt": attempt_no, "http": status, "data": data}, separators=(",", ":")))
    if status == 200:
        break
    attempts_now = data.get("provider_attempts") or []
    zero_spend_quota = (
        status == 503 and data.get("status") == "NO_ZERO_SPEND_MULTIMODAL_CAPACITY"
        and data.get("mandatory_cost_usd") == 0 and data.get("paid_fallback_used") is False
        and any(a.get("free_plan_proven") is True and a.get("status") == 429 for a in attempts_now)
    )
    if not zero_spend_quota or attempt_no == 15:
        break
    time.sleep(60)
assert status == 200, (status, data)
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