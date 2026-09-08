import json
import os
import urllib.request
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
    def _decide(self, oidc: str, instruction: str, observation: str, step: int) -> dict:
        payload = json.dumps({"instruction": instruction, "observation": observation, "step": step}).encode()
        req = urllib.request.Request(API_URL, data=payload, method="POST", headers={
            "Authorization": "Bearer " + oidc,
            "Content-Type": "application/json",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode())
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
        for step in range(1, MAX_STEPS + 1):
            decision = self._decide(oidc, instruction, observation, step)
            action = decision["action"]
            providers.append({"provider": decision.get("provider"), "model": decision.get("model")})
            trace.append({"step": step, "action": action.get("action"), "command": action.get("command", ""), "summary": action.get("summary", "")})
            if action.get("action") == "finish":
                break
            result = await environment.exec(command=str(action["command"]), timeout_sec=120)
            observation = "RETURN_CODE: %s\nSTDOUT:\n%s\nSTDERR:\n%s" % (
                result.return_code, (result.stdout or "")[-12000:], (result.stderr or "")[-12000:]
            )
        context.cost_usd = 0.0
        context.metadata = {"pipeline": "terminal-agent-v2-free-mesh", "trace": trace, "providers": providers, "steps": len(trace)}
