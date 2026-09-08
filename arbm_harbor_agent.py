import json
import os
import urllib.request
import urllib.error
import time
import random
from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

API_URL = "https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v2"
SOVEREIGN_URL = os.environ.get("ARBM_SOVEREIGN_URL", "http://127.0.0.1:8088/v1/chat/completions")
MAX_STEPS = 8

class ARBMHarborAgent(BaseAgent):
    @staticmethod
    def name() -> str:
        return "arbm-sist"

    def version(self) -> str | None:
        return "terminal-v2-free-mesh"

    async def setup(self, environment: BaseEnvironment) -> None:
        return None

    def _oidc(self) -> str:
        url = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_URL", "")
        token = os.environ.get("ACTIONS_ID_TOKEN_REQUEST_TOKEN", "")
        if not url or not token:
            raise RuntimeError("GITHUB_OIDC_UNAVAILABLE")
        sep = "&" if "?" in url else "?"
        req = urllib.request.Request(url + sep + "audience=arbm-sist-benchmark", headers={"Authorization": "Bearer " + token})
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode())["value"]
    def _sovereign_decide(self, instruction: str, observation: str, step: int) -> dict:
        prompt = f"""You are ARBM SIST inside a Terminal-Bench sandbox. Return JSON only with action, command, summary. action must be exec or finish. Use one safe bash command for exec. Never access evaluator secrets, credentials, or files outside the sandbox. Do not repeat failed commands. Inspect first, make the smallest correct change, run a focused verification, and finish only after verification succeeds. Keep commands bounded and non-interactive.\nSTEP:{step}\nTASK:{instruction}\nRECENT HISTORY:{observation}"""
        body = {"model":"arbm-qwen-sovereign","messages":[{"role":"user","content":prompt}],"temperature":0,"max_tokens":160}
        req = urllib.request.Request(SOVEREIGN_URL, data=json.dumps(body).encode(), method="POST", headers={"Authorization":"Bearer local-dummy-key","Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=150) as r:
            raw=json.loads(r.read().decode())
        text=str((((raw.get("choices") or [{}])[0].get("message") or {}).get("content") or "")).strip()
        text=text.removeprefix("```json").removesuffix("```").strip()
        start=text.find("{"); end=text.rfind("}")
        if start >= 0 and end > start: text=text[start:end+1]
        action=json.loads(text)
        if action.get("action") not in ("exec","finish") or (action.get("action")=="exec" and not str(action.get("command","")).strip()):
            raise RuntimeError("ARBM_SOVEREIGN_INVALID_ACTION")
        return {"ok":True,"status":"PASS","action":action,"model":"arbm-qwen-sovereign","provider":"sovereign-qwen-github","provider_attempts":[{"route":"sovereign","status":200,"model":"arbm-qwen-sovereign"}],"mandatory_cost_usd":0,"paid_fallback_used":False}

    def _decide(self, instruction: str, observation: str, step: int) -> dict:
        payload = json.dumps({"instruction": instruction, "observation": observation, "step": step}).encode()
        last_error = None
        cooldown_until = getattr(self, "_remote_cooldown_until", 0.0)
        if time.time() < cooldown_until and os.environ.get("ARBM_ENABLE_SOVEREIGN_FALLBACK") == "1":
            return self._sovereign_decide(instruction, observation, step)
        for attempt in range(4):
            try:
                oidc = self._oidc()
                req = urllib.request.Request(API_URL, data=payload, method="POST", headers={
                    "Authorization": "Bearer " + oidc,
                    "Content-Type": "application/json",
                })
                with urllib.request.urlopen(req, timeout=35) as r:
                    body = json.loads(r.read().decode())
                if not body.get("ok"):
                    raise RuntimeError("ARBM_DECISION_UNAVAILABLE:" + str(body.get("status") or body.get("error")))
                if float(body.get("mandatory_cost_usd", -1)) != 0 or body.get("paid_fallback_used") is not False:
                    raise RuntimeError("ARBM_ZERO_COST_POLICY_VIOLATION")
                return body
            except urllib.error.HTTPError as exc:
                body_text = exc.read().decode("utf-8", "replace")[:4000]
                try:
                    safe = json.loads(body_text)
                    detail = json.dumps({"status": safe.get("status"), "error": safe.get("error"), "provider_attempts": safe.get("provider_attempts", [])}, separators=(",", ":"))
                except Exception:
                    detail = "unparsed"
                last_error = "HTTP_%s:%s" % (exc.code, detail)
                if exc.code == 503:
                    waits = []
                    for item in safe.get("provider_attempts", []):
                        if str(item.get("route") or "").startswith("groq") and item.get("status") == 429:
                            raw = str(item.get("retry_after") or "").strip().lower()
                            try:
                                waits.append(float(raw.rstrip("s")))
                            except Exception:
                                waits.append(20.0)
                    if waits:
                        wait=max(waits)
                        if wait > 60:
                            self._remote_cooldown_until = time.time() + min(wait, 600.0)
                            break
                        time.sleep(wait + 1.0)
                if exc.code not in (401, 408, 429, 500, 502, 503, 504):
                    raise RuntimeError("ARBM_DECISION_HTTP_%s" % exc.code)
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = type(exc).__name__
            if attempt < 3:
                time.sleep((0.7 * (2 ** attempt)) + random.uniform(0.05, 0.25))
        if os.environ.get("ARBM_ENABLE_SOVEREIGN_FALLBACK") == "1":
            try:
                return self._sovereign_decide(instruction, observation, step)
            except Exception as exc:
                raise RuntimeError("ARBM_DECISION_ALL_FREE_ROUTES_EXHAUSTED:remote=%s;sovereign=%s" % (last_error, type(exc).__name__))
        raise RuntimeError("ARBM_DECISION_RETRY_EXHAUSTED:" + str(last_error))

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        observation = "No commands executed yet."
        trace = []
        providers = []
        recent_commands = []
        history = []
        for step in range(1, MAX_STEPS + 1):
            compact = "\n\n".join(history[-1:] + [observation])[-1200:]
            decision = self._decide(instruction, compact, step)
            action = decision["action"]
            command = str(action.get("command", "")).strip()
            providers.append({"provider": decision.get("provider"), "model": decision.get("model"), "attempts": decision.get("provider_attempts", [])})
            if action.get("action") == "finish":
                trace.append({"step": step, "action": "finish", "summary": action.get("summary", "")})
                break
            if command in recent_commands[-3:]:
                observation = "ANTI_LOOP: command was already executed recently and was NOT run again. Choose a materially different diagnostic or repair strategy.\nREJECTED_COMMAND: " + command
                history.append(observation)
                trace.append({"step": step, "action": "rejected_repeat", "command": command, "summary": action.get("summary", "")})
                continue
            result = await environment.exec(command=command, timeout_sec=120)
            recent_commands.append(command)
            observation = "RETURN_CODE: %s\nSTDOUT:\n%s\nSTDERR:\n%s" % (
                result.return_code, (result.stdout or "")[-10000:], (result.stderr or "")[-10000:]
            )
            history.append("COMMAND: %s\n%s" % (command, observation))
            trace.append({"step": step, "action": "exec", "command": command, "summary": action.get("summary", ""), "return_code": result.return_code})
        context.cost_usd = 0.0
        context.metadata = {"pipeline": "terminal-agent-v4-free-mesh-resilient", "trace": trace, "providers": providers, "steps": len(trace)}

