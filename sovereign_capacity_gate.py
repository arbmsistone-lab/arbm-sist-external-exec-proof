import json
from pathlib import Path

EVIDENCE = Path("evidence/SOVEREIGN-3M-CAPACITY-20260909.json")
TARGET = 3_000_000
MIN_TPS = TARGET / 86_400


def certify_sovereign_capacity():
    try:
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"certified": False, "status": "FAIL_MISSING_OR_INVALID_SOVEREIGN_EVIDENCE"}
    shards = data.get("shards") or []
    rotations = data.get("rotation_generations") or []
    ok = (
        data.get("zero_spend_mode") == "HARD"
        and data.get("throughput_gate") == "PASS"
        and data.get("rotation_gate") == "PASS"
        and len(shards) == 4
        and sorted(s.get("id") for s in shards) == [1, 2, 3, 4]
        and float(data.get("aggregate_tokens_per_s", 0)) >= MIN_TPS
        and int(data.get("projected_daily_tokens", 0)) >= TARGET
        and rotations == [0, 1, 2]
        and len(data.get("rotation_runs") or []) == 3
    )
    return {
        "certified": ok,
        "status": "PASS_QUANTITATIVE_SOVEREIGN_CAPACITY" if ok else "FAIL_INVALID_SOVEREIGN_EVIDENCE",
        "throughput_run": data.get("throughput_run"),
        "aggregate_tokens_per_s": data.get("aggregate_tokens_per_s"),
        "projected_daily_tokens": data.get("projected_daily_tokens"),
        "target_daily_tokens": TARGET,
        "rotation_runs": data.get("rotation_runs"),
        "scope": data.get("claim_scope"),
    }
