import json
import os
import urllib.request
import urllib.error
import time
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
        return "terminal-v3-free-mesh-hard-gate"

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
    def _decide(self, oidc: str, instruction: str, observation: str, step: int) -> dict:
        payload = json.dumps({"instruction": instruction, "observation": observation, "step": step}).encode()
        req = urllib.request.Request(API_URL, data=payload, method="POST", headers={
            "Authorization": "Bearer " + oidc,
            "Content-Type": "application/json",
        })
        body = None
        last_error = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    body = json.loads(r.read().decode())
                break
            except urllib.error.HTTPError as exc:
                last_error = exc
                if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
                time.sleep(1 + attempt)
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = exc
                if attempt == 2:
                    raise
                time.sleep(1 + attempt)
        if body is None:
            raise RuntimeError("ARBM_DECISION_TRANSPORT_FAILED:" + str(last_error))
        if not body.get("ok"):
            raise RuntimeError("ARBM_DECISION_UNAVAILABLE:" + str(body.get("status") or body.get("error")))
        if float(body.get("mandatory_cost_usd", -1)) != 0 or body.get("paid_fallback_used") is not False:
            raise RuntimeError("ARBM_ZERO_COST_POLICY_VIOLATION")
        return body

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        oidc = self._oidc()
        observation = "No commands executed yet."
        trace = []
        providers = []
        failed_commands = set()
        for step in range(1, MAX_STEPS + 1):
            decision = self._decide(oidc, instruction, observation, step)
            action = decision["action"]
            providers.append({"provider": decision.get("provider"), "model": decision.get("model")})
            command = str(action.get("command", "")).strip()
            trace.append({"step": step, "action": action.get("action"), "command": command, "summary": action.get("summary", "")})
            if action.get("action") == "finish":
                break
            if command in failed_commands:
                observation = "REJECTED_REPEAT_FAILED_COMMAND:\n%s\nChoose a materially different diagnostic or repair strategy." % command
                continue
            result = await environment.exec(command=command, timeout_sec=120)
            observation = "RETURN_CODE: %s\nSTDOUT:\n%s\nSTDERR:\n%s" % (
                result.return_code, (result.stdout or "")[-12000:], (result.stderr or "")[-12000:]
            )
            if result.return_code != 0:
                failed_commands.add(command)
                observation += "\nRECOVERY_DIRECTIVE: this exact command failed and must not be repeated."
        context.cost_usd = 0.0
        context.metadata = {"pipeline": "terminal-agent-v2-free-mesh", "trace": trace, "providers": providers, "steps": len(trace)}
