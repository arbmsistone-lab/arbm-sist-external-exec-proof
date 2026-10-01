from __future__ import annotations
from pathlib import Path
import json,sys

ROOT=Path(__file__).resolve().parent.parent
CFG=ROOT/"stage7"/"baseline_config.json"

def load_config():
    if not CFG.exists():
        raise SystemExit("BASELINE_BLOCKED_CONFIG_MISSING")
    c=json.loads(CFG.read_text(encoding="utf-8"))
    required=["provider","model_id","temperature","max_output_tokens","max_agent_steps","max_wall_time_seconds","max_model_calls","max_paid_cost_usd"]
    missing=[k for k in required if c.get(k) is None]
    if missing:
        raise SystemExit("BASELINE_BLOCKED_CONFIG_INCOMPLETE:"+",".join(missing))
    if float(c["max_paid_cost_usd"])!=0.0:
        raise SystemExit("BASELINE_BLOCKED_PAID_COST_NOT_ZERO")
    if c.get("frozen") is not True:
        raise SystemExit("BASELINE_BLOCKED_CONFIG_NOT_FROZEN")
    return c

if __name__=="__main__":
    load_config()
    raise SystemExit("BASELINE_MODEL_EXECUTION_NOT_IMPLEMENTED_UNTIL_STAGE6_PASS")
