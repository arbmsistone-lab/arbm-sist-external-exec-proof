import json, os, re, time, urllib.request, urllib.error, hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v5"
EXPECTED_PIPELINE = "arbm-osworld-v31-isolated"
EXPECTED_BUILD = "arbm-osworld-v31k-isolated-20260911"
MAX_NO_PROGRESS = int(os.environ.get("ARBM_MAX_NO_PROGRESS", "12"))
MAX_WAIT_RESPONSES = int(os.environ.get("ARBM_MAX_WAIT_RESPONSES", "20"))
STATE = {
    "step": 0, "previous": "", "executed": 0, "phase": "execute",
    "plan": "", "memory": [], "verification": "", "history": [],
    "last_obs_sig": "", "no_progress": 0, "wait_responses": 0,
}
LOG = os.environ.get("ARBM_OSWORLD_SHIM_LOG", "osworld-v31-shim.log")


def content_parts(content):
    texts, images = [], []
    if isinstance(content, str):
        texts.append(content)
    elif isinstance(content, list):
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text":
                texts.append(str(item.get("text") or ""))
            elif item.get("type") == "image_url":
                image = item.get("image_url") or {}
                url = image.get("url") if isinstance(image, dict) else ""
                if isinstance(url, str) and url.startswith("data:image/"):
                    images.append(url)
    return "\n".join(texts), images

def oidc_token():
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    token = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(url + sep + "audience=arbm-sist-benchmark",
                                 headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=20) as res:
        return json.loads(res.read())["value"]


def task_from(messages):
    system = "\n".join(content_parts(m.get("content"))[0]
                       for m in messages if m.get("role") == "system")
    match = re.search(r"You are asked to complete the following task:\s*(.*)$", system, re.S)
    return (match.group(1).strip() if match else system[-18000:])


def latest_observation(messages):
    users = [m for m in messages if m.get("role") == "user"]
    if not users:
        return "", ""
    text, images = content_parts(users[-1].get("content"))
    if len(text) > 24000:
        first = 8000
        text = text[:first] + "\n...[middle compressed]...\n" + text[-16000:]
    image = images[-1] if images else ""
    if len(image) > 26_000_000:
        image = ""
    return text, image


def memory_text():
    blocks = []
    if STATE["plan"]:
        blocks.append("PLAN:\n" + STATE["plan"][-3500:])
    blocks.extend(STATE["memory"][-18:])
    if STATE["verification"]:
        blocks.append("LAST_VERIFICATION:\n" + STATE["verification"][-2500:])
    return "\n\n".join(blocks)[-18000:]


def log_event(data):
    safe = {k: data.get(k) for k in
            ("step", "http", "status", "provider", "model", "pipeline", "agent_build")}
    safe["phase"] = STATE["phase"]
    safe["no_progress"] = STATE["no_progress"]
    safe["attempts"] = [{k: a.get(k) for k in
                         ("route", "model", "status", "parsed", "free_plan_proven", "reason")}
                        for a in (data.get("provider_attempts") or [])]
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(safe, separators=(",", ":")) + "\n")


def update_state(action, obs_sig):
    patch = str(action.get("memory_patch") or "").strip()
    if patch:
        STATE["memory"].append(f"step {STATE['step']}: {patch[:3500]}")
        STATE["memory"] = STATE["memory"][-18:]
    plan = str(action.get("plan") or "").strip()
    if plan:
        STATE["plan"] = plan[:3500]
    verification = str(action.get("verification") or "").strip()
    if verification:
        STATE["verification"] = verification[:2500]
    phase = str(action.get("phase") or "execute")
    if phase in ("plan", "execute", "verify", "done"):
        STATE["phase"] = phase
    if obs_sig != STATE["last_obs_sig"]:
        STATE["no_progress"] = 0
    STATE["last_obs_sig"] = obs_sig


def call_mesh(messages):
    STATE["step"] += 1
    if STATE["no_progress"] >= MAX_NO_PROGRESS or STATE["wait_responses"] >= MAX_WAIT_RESPONSES:
        log_event({"step": STATE["step"], "http": 200, "status": "NO_PROGRESS_ABORT", "provider": "guardrail", "model": "none", "pipeline": EXPECTED_PIPELINE, "agent_build": EXPECTED_BUILD})
        return "FAIL"
    obs, screenshot = latest_observation(messages)
    obs_sig = hashlib.sha256(obs.encode("utf-8", "ignore")).hexdigest()[:20]
    body = {
        "instruction": "ACTION CONTRACT: field action MUST be exactly one of exec, finish, wait. Planning belongs only in field plan/phase; never return action=plan/execute/click/type. If GUI work remains, use action=exec with a direct pyautogui command.\n\n" + task_from(messages), "observation": obs,
        "screenshot_data_url": screenshot,
        "visual_context": "latest OSWorld screenshot attached" if screenshot else "screenshot unavailable",
        "previous_command": STATE["previous"], "executed_count": STATE["executed"],
        "memory": memory_text(), "phase": "execute",
        "no_progress_count": STATE["no_progress"], "step": STATE["step"],
    }
    http, data = None, {"status": "NO_ATTEMPT"}
    for attempt in range(4):
        req = urllib.request.Request(
            UPSTREAM, data=json.dumps(body).encode(), method="POST",
            headers={"Authorization": "Bearer " + oidc_token(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=75) as res:
                http, data = res.status, json.loads(res.read())
        except urllib.error.HTTPError as err:
            http = err.code
            try:
                data = json.loads(err.read())
            except Exception:
                data = {"status": "INVALID_UPSTREAM_RESPONSE"}
        if http == 200:
            break
        if http == 422 and data.get("status") in ("INVALID_ACTION", "ACTION_REJECTED"):
            body["phase"] = "execute"
            body["memory"] = (str(body.get("memory") or "") + "\nRECOVERY: return action=exec with direct pyautogui.* command only, or action=finish only if visibly complete.")[-18000:]
            time.sleep(0.4)
            continue
        if http not in (429, 503):
            break
        time.sleep(1.0 + attempt * 0.5)
    data["step"], data["http"] = STATE["step"], http
    log_event(data)
    if http != 200 or data.get("ok") is not True:
        STATE["no_progress"] += 1
        STATE["phase"] = "execute"
        STATE["wait_responses"] += 1
        return "WAIT"
    if data.get("pipeline") != EXPECTED_PIPELINE or data.get("agent_build") != EXPECTED_BUILD:
        STATE["no_progress"] += 1
        STATE["wait_responses"] += 1
        return "WAIT"
    action = data.get("action") or {}
    previous_obs_sig = STATE["last_obs_sig"]
    update_state(action, obs_sig)
    kind = action.get("action")
    if kind == "exec":
        command = str(action.get("command") or "").strip()
        if not command:
            STATE["no_progress"] += 1
            return "WAIT"
        same_state = obs_sig == previous_obs_sig
        if command == STATE["previous"] and same_state:
            STATE["no_progress"] += 1
            STATE["phase"] = "execute"
            return "WAIT"
        STATE["previous"] = command
        STATE["executed"] += 1
        STATE["wait_responses"] = 0
        STATE["history"].append({"step": STATE["step"], "command": command[:1200], "obs": obs_sig})
        STATE["history"] = STATE["history"][-24:]
        return "```python\n" + command + "\n```"
    if kind == "finish":
        confidence = float(action.get("confidence") or 0)
        verification = str(action.get("verification") or "").strip()
        if confidence >= 0.72 and verification:
            STATE["wait_responses"] = 0
            return "DONE"
        STATE["wait_responses"] += 1
        return "WAIT"
    STATE["no_progress"] += 1
    STATE["wait_responses"] += 1
    if STATE["no_progress"] >= 2:
        STATE["phase"] = "execute"
    return "WAIT"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return
    def send_json(self, code, value):
        raw = json.dumps(value).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok", "pipeline": EXPECTED_PIPELINE, "build": EXPECTED_BUILD})
        else:
            self.send_json(404, {})
    def do_POST(self):
        if self.path != "/v1/chat/completions":
            return self.send_json(404, {})
        try:
            n = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(n) or b"{}")
            content = call_mesh(body.get("messages") or [])
            self.send_json(200, {
                "id": "arbm-osworld-v31-isolated", "object": "chat.completion", "created": int(time.time()),
                "model": "gpt-arbm-osworld-v31-isolated",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            })
        except RuntimeError as exc:
            log_event({"step": STATE["step"], "http": 503, "status": str(exc)})
            self.send_json(503, {"error": {"message": str(exc), "type": "server_error", "param": None, "code": "arbm_no_progress_abort"}})
        except Exception as exc:
            log_event({"step": STATE["step"], "http": None, "status": type(exc).__name__})
            self.send_json(500, {"error": {"message": type(exc).__name__, "type": "server_error", "param": None, "code": "shim_internal_error"}})


ThreadingHTTPServer(("127.0.0.1", 8088), Handler).serve_forever()