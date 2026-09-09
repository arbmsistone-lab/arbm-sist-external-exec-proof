import json, os, re, time, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v7"
STATE = {"step": 0, "previous": ""}
LOG = os.environ.get("ARBM_OSWORLD_SHIM_LOG", "osworld-free-mesh-shim.log")

def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(x.get("text", "")) for x in content if isinstance(x, dict) and x.get("type") == "text")
    return str(content or "")

def oidc_token():
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"]
    token = os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"]
    sep = "&" if "?" in url else "?"
    req = urllib.request.Request(url + sep + "audience=arbm-sist-benchmark", headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=20) as res:
        return json.loads(res.read())["value"]

def task_from(messages):
    system = "\n".join(text_of(m.get("content")) for m in messages if m.get("role") == "system")
    match = re.search(r"You are asked to complete the following task:\s*(.*)$", system, re.S)
    return match.group(1).strip() if match else system[-10000:]

def latest_observation(messages):
    users = [text_of(m.get("content")) for m in messages if m.get("role") == "user"]
    return users[-1][-26000:] if users else ""

def log_event(data):
    safe = {k: data.get(k) for k in ("step", "http", "status", "provider", "model")}
    safe["attempts"] = [{k: a.get(k) for k in ("route", "model", "status", "parsed", "reason")}
                        for a in (data.get("provider_attempts") or [])]
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(safe, separators=(",", ":")) + "\n")

def call_mesh(messages):
    STATE["step"] += 1
    body = {"instruction": task_from(messages), "observation": latest_observation(messages),
            "previous_command": STATE["previous"], "step": STATE["step"]}
    req = urllib.request.Request(UPSTREAM, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + oidc_token(), "Content-Type": "application/json"})
    http = None
    try:
        with urllib.request.urlopen(req, timeout=70) as res:
            http, data = res.status, json.loads(res.read())
    except urllib.error.HTTPError as err:
        http = err.code
        try: data = json.loads(err.read())
        except Exception: data = {"status": "INVALID_UPSTREAM_RESPONSE"}
    data["step"], data["http"] = STATE["step"], http
    log_event(data)
    action = data.get("action") or {}
    if http == 200 and data.get("ok") is True and action.get("action") == "exec":
        command = str(action.get("command") or "").strip()
        STATE["previous"] = command
        return "```python\n" + command + "\n```"
    if http == 200 and data.get("ok") is True and action.get("action") == "finish":
        return "DONE"
    return "WAIT"

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return
    def send_json(self, code, value):
        raw = json.dumps(value).encode()
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        self.send_json(200, {"status": "ok"}) if self.path == "/health" else self.send_json(404, {})
    def do_POST(self):
        if self.path != "/v1/chat/completions": return self.send_json(404, {})
        try:
            n = int(self.headers.get("Content-Length", "0")); body = json.loads(self.rfile.read(n) or b"{}")
            content = call_mesh(body.get("messages") or [])
            self.send_json(200, {"id": "arbm-osworld-free-mesh", "object": "chat.completion",
                "created": int(time.time()), "model": "gpt-arbm-sovereign",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}})
        except Exception as exc:
            log_event({"step": STATE["step"], "http": None, "status": type(exc).__name__})
            self.send_json(200, {"choices": [{"message": {"role": "assistant", "content": "WAIT"}}]})

ThreadingHTTPServer(("127.0.0.1", 8088), Handler).serve_forever()
