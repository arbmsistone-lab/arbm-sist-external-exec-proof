import json
import os
import urllib.error
import urllib.request
from typing import override

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

ENDPOINT = "https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v1"
BLOCKED = (
    "/logs/verifier", "reward.txt", "verifier", "GEMINI_API_KEY",
    "ACTIONS_ID_TOKEN", "SUPABASE_SERVICE_ROLE", "OPENAI_API_KEY",
    "solution.sh", "/tests/", "test_output", "ground_truth",
)

class ArbMSistAgent(BaseAgent):
    @staticmethod
    @override
    def name() -> str:
        return "arbm-sist"

    @override
    def version(self) -> str:
        return "1.0.0"

    @override
    async def setup(self, environment: BaseEnvironment) -> None:
        return None

    def _call_brain(self, instruction: str, observation: str, step: int) -> dict:
        token = os.environ.get("ARBM_OIDC_TOKEN", "").strip()
        if not token:
            raise RuntimeError("ARBM_OIDC_TOKEN_MISSING")
        payload = json.dumps({
            "instruction": instruction,
            "observation": observation,
            "step": step,
        }).encode()
        req = urllib.request.Request(
            ENDPOINT,
            data=payload,
            method="POST",
            headers={
                "authorization": f"Bearer {token}",
                "content-type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as res:
                return json.loads(res.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:800]
            raise RuntimeError(f"ARBM_BRAIN_HTTP_{exc.code}:{detail}") from exc

    @staticmethod
    def _safe_command(command: str) -> bool:
        low = command.lower()
        return not any(term.lower() in low for term in BLOCKED)

    @override
    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        observation = "No commands executed yet."
        trace = []
        for step in range(1, 31):
            reply = self._call_brain(instruction, observation, step)
            if reply.get("ok") is not True:
                raise RuntimeError(f"ARBM_BRAIN_NOT_READY:{reply.get('status')}")
            action = reply.get("action") or {}
            kind = str(action.get("action") or "")
            summary = str(action.get("summary") or "")[:1000]
            if kind == "finish":
                trace.append({"step": step, "action": "finish", "summary": summary})
                context.cost_usd = 0.0
                context.metadata = {"pipeline": "arbm-terminal-agent-v1", "steps": trace}
                return
            if kind != "exec":
                raise RuntimeError(f"ARBM_INVALID_ACTION:{kind}")
            command = str(action.get("command") or "").strip()
            if not command or not self._safe_command(command):
                raise RuntimeError("ARBM_COMMAND_BLOCKED")
            result = await environment.exec(command=command, timeout_sec=120)
            stdout = (result.stdout or "")[-6000:]
            stderr = (result.stderr or "")[-3000:]
            observation = (
                f"COMMAND:\n{command}\nRETURN_CODE:{result.return_code}"
                f"\nSTDOUT:\n{stdout}\nSTDERR:\n{stderr}"
            )
            trace.append({
                "step": step,
                "action": "exec",
                "command": command[:1000],
                "return_code": result.return_code,
                "summary": summary,
            })
        context.cost_usd = 0.0
        context.metadata = {"pipeline": "arbm-terminal-agent-v1", "steps": trace}
        raise RuntimeError("ARBM_STEP_LIMIT_EXCEEDED")
