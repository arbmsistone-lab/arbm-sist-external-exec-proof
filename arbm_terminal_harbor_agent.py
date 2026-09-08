import json
import os
import urllib.error
import urllib.request
from harbor.agents.base import BaseAgent

ENDPOINT = os.environ.get(
    "ARBM_TERMINAL_ENDPOINT",
    "https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-terminal-agent-v1",
)


def _call_agent(instruction: str, observation: str, step: int) -> dict:
    token = os.environ.get("ARBM_TERMINAL_OIDC", "").strip()
    if not token:
        raise RuntimeError("terminal_oidc_required")
    body = json.dumps({
        "instruction": instruction,
        "observation": observation,
        "step": step,
    }).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=body, method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            data = json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[-1000:]
        raise RuntimeError(f"terminal_backend_http_{exc.code}:{detail}") from exc
    if data.get("ok") is not True or data.get("status") != "PASS":
        raise RuntimeError("terminal_backend_not_ready:" + str(data.get("status")))
    if data.get("scoreable") is not False:
        raise RuntimeError("terminal_backend_scoreable_contract_violation")
    if float(data.get("mandatory_cost_usd", 1)) != 0:
        raise RuntimeError("terminal_backend_cost_contract_violation")
    action = data.get("action") or {}
    if action.get("action") not in {"exec", "finish"}:
        raise RuntimeError("terminal_backend_invalid_action")
    if action.get("action") == "exec" and not str(action.get("command", "")).strip():
        raise RuntimeError("terminal_backend_empty_command")
    return data


class ARBMTerminalAgent(BaseAgent):
    SUPPORTS_ATIF = False
    SUPPORTS_RESUME = False

    @staticmethod
    def name() -> str:
        return "arbm-terminal-p3-smoke"

    def version(self) -> str | None:
        return "p3-terminal-agent-v1-nonscoreable"

    async def setup(self, environment) -> None:
        return None
    async def run(self, instruction: str, environment, context) -> None:
        observation = "No commands have been executed yet."
        steps = []
        max_steps = max(1, min(8, int(os.environ.get("ARBM_TERMINAL_MAX_STEPS", "3"))))
        for step in range(1, max_steps + 1):
            data = _call_agent(instruction, observation, step)
            action = data["action"]
            if action["action"] == "finish":
                steps.append({"step": step, "action": "finish", "summary": action.get("summary", "")})
                break
            command = str(action["command"]).strip()
            result = await environment.exec(command, timeout_sec=120)
            observation = json.dumps({
                "returnCode": result.return_code,
                "stdout": (result.stdout or "")[-8000:],
                "stderr": (result.stderr or "")[-8000:],
            })
            steps.append({"step": step, "action": "exec", "command": command[:1000], "returnCode": result.return_code})
        context.cost_usd = 0.0
        context.metadata = {
            "arbmVersion": self.version(),
            "pipeline": "terminal-agent-v1",
            "scoreable": False,
            "mandatorySpendUsd": 0,
            "paidFallbackUsed": False,
            "remoteOnly": True,
            "steps": steps,
        }
        evidence_path = os.environ.get("ARBM_TERMINAL_EVIDENCE_PATH", "").strip()
        if evidence_path:
            with open(evidence_path, "w", encoding="utf-8") as handle:
                json.dump(context.metadata, handle, indent=2)
                handle.write("\n")
