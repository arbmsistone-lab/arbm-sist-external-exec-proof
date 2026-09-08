from pathlib import Path

TERMINAL_DATASET="terminal-bench/terminal-bench-2-1"
OSWORLD_NAME="OSWorld-Verified"

def terminal_command(agent_import: str) -> list[str]:
    if not agent_import or ":" not in agent_import:
        raise ValueError("TERMINAL_AGENT_IMPORT_INVALID")
    return ["harbor","run","-d",TERMINAL_DATASET,"--agent-import-path",agent_import,"-k","5"]

def validate_terminal_evidence(root: Path) -> list[str]:
    required=("job.json","results.json","trajectories","SHA256SUMS.txt")
    return [f"TERMINAL_EVIDENCE_MISSING:{name}" for name in required if not (root/name).exists()]

def validate_osworld_evidence(root: Path) -> list[str]:
    required=("result.json","trajectories","monitor","agent-implementation","SHA256SUMS.txt")
    return [f"OSWORLD_EVIDENCE_MISSING:{name}" for name in required if not (root/name).exists()]

def certified_external(result: dict, evidence_failures: list[str]) -> bool:
    return result.get("verified_by_maintainer") is True and not evidence_failures
