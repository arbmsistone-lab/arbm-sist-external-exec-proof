import json
import os
import urllib.request
import urllib.error
import time
import random
from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

API_URL = "https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v1"
MAX_STEPS = 20

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
    def _decide(self, instruction: str, observation: str, step: int) -> dict:
        payload = json.dumps({"instruction": instruction, "observation": observation, "step": step}).encode()
        last_error = None
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
                        if item.get("route") == "groq" and item.get("status") == 429:
                            raw = str(item.get("retry_after") or "").strip().lower()
                            try:
                                waits.append(float(raw.rstrip("s")))
                            except Exception:
                                waits.append(20.0)
                    if waits:
                        time.sleep(min(max(waits) + 1.0, 65.0))
                if exc.code not in (401, 408, 429, 500, 502, 503, 504):
                    raise RuntimeError("ARBM_DECISION_HTTP_%s" % exc.code)
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = type(exc).__name__
            if attempt < 3:
                time.sleep((0.7 * (2 ** attempt)) + random.uniform(0.05, 0.25))
        raise RuntimeError("ARBM_DECISION_RETRY_EXHAUSTED:" + str(last_error))

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        observation = "No commands executed yet."
        trace = []
        providers = []
        recent_commands = []
        history = []
        for step in range(1, MAX_STEPS + 1):
            compact = "\n\n".join(history[-2:] + [observation])[-3500:]
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
