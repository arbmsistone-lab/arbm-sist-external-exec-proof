import json
import os
import urllib.error
import urllib.request
from harbor.agents.base import BaseAgent

ENDPOINT = os.environ.get("ARBM_TERMINAL_ENDPOINT", "https://arbm-p0-free-proof.zevanory.workers.dev")
MODEL = "@cf/nvidia/nemotron-3-120b-a12b"

def _call_agent(instruction: str, observation: str, step: int) -> dict:
    token = os.environ.get("ARBM_TERMINAL_OIDC", "").strip()
    if not token:
        raise RuntimeError("terminal_oidc_required")
    prompt = (
        "You are ARBM SIST inside a Terminal-Bench sandbox. Return JSON only with action exec or finish, command, and summary. "
        "Use exactly one safe bash command per exec. Never access hidden evaluator data or credentials. Finish only after verification.\n"
        f"STEP:{step}\nTASK:\n{instruction[:16000]}\nLAST OBSERVATION:\n{observation[-16000:]}"
    )
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}]}).encode("utf-8")
    req = urllib.request.Request(ENDPOINT, data=body, method="POST")
    req.add_header("content-type", "application/json")
    req.add_header("authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=45) as res:
            data = json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"terminal_backend_http_{exc.code}") from exc
    if data.get("ok") is not True or data.get("provider") != "cloudflare":
        raise RuntimeError("terminal_backend_contract_violation")
    if float(data.get("mandatory_cost_usd", 1)) != 0 or data.get("paid_fallback_used") is not False:
        raise RuntimeError("terminal_backend_cost_contract_violation")
    raw = (((data.get("result") or {}).get("choices") or [{}])[0].get("message") or {}).get("content", "")
    text = str(raw).strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    try:
        action = json.loads(text.strip())
    except Exception as exc:
        raise RuntimeError("terminal_backend_invalid_json") from exc
    if action.get("action") not in {"exec", "finish"}:
        raise RuntimeError("terminal_backend_invalid_action")
    if action.get("action") == "exec" and not str(action.get("command", "")).strip():
        raise RuntimeError("terminal_backend_empty_command")
    return {"ok": True, "status": "PASS", "scoreable": False, "mandatory_cost_usd": 0,
            "paid_fallback_used": False, "provider": "cloudflare", "model": data.get("model"), "action": action}

class ARBMTerminalAgent(BaseAgent):
    SUPPORTS_ATIF = False
    SUPPORTS_RESUME = False

    @staticmethod
    def name() -> str:
        return "arbm-terminal-p3-cloudflare-dev"
    def version(self) -> str | None:
        return "p3-terminal-cloudflare-dev-v1"

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
            observation = json.dumps({"returnCode": result.return_code, "stdout": (result.stdout or "")[-8000:], "stderr": (result.stderr or "")[-8000:]})
            steps.append({"step": step, "action": "exec", "command": command[:1000], "returnCode": result.return_code})
        context.cost_usd = 0.0
        context.metadata = {"arbmVersion": self.version(), "pipeline": "terminal-cloudflare-dev-v1", "scoreable": False,
                            "mandatorySpendUsd": 0, "paidFallbackUsed": False, "remoteOnly": True, "provider": "cloudflare", "model": MODEL, "steps": steps}
        evidence_path = os.environ.get("ARBM_TERMINAL_EVIDENCE_PATH", "").strip()
        if evidence_path:
            with open(evidence_path, "w", encoding="utf-8") as handle:
                json.dump(context.metadata, handle, indent=2)
                handle.write("\n")