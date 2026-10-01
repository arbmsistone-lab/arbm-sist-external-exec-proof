from __future__ import annotations
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parent.parent
probe=ROOT/"logs"/"stage6_openrouter_probe.json"
if not probe.exists():
    print("BASELINE_PREFLIGHT=BLOCKED")
    print("REASON=OPENROUTER_M0_PROBE_MISSING")
    raise SystemExit(2)

j=json.loads(probe.read_text(encoding="utf-8-sig"))
checks={
 "M0_STATUS_PASS": j.get("status")=="PASS",
 "RUNTIME_PROBE_PASS": j.get("runtime_probe")=="PASS",
 "THIRTY_RUNS_FIT": j.get("thirty_valid_runs_fit") is True,
 "MAX_PAID_COST_ZERO": float(j.get("max_paid_cost_usd",1))==0.0,
 "AUTO_PAID_DISABLED": j.get("auto_paid_upgrade_allowed") is False,
 "BILLING_STATE_KNOWN": j.get("account_billing_state") not in (None,"","UNKNOWN"),
 "MODEL_ID_KNOWN": j.get("account_exact_model_id") not in (None,"","UNKNOWN"),
 "MODEL_PRICE_ZERO": float(j.get("model_price_prompt_usd_per_million",1))==0.0 and float(j.get("model_price_completion_usd_per_million",1))==0.0,
}
for k,v in checks.items():
    print(f"{k}={'PASS' if v else 'FAIL'}")
ok=all(checks.values())
print("BASELINE_PREFLIGHT=PASS" if ok else "BASELINE_PREFLIGHT=BLOCKED")
print("MODEL_CALLS_EXECUTED_BY_PREFLIGHT=0")
print("PAID_COST_USD=0.00")
raise SystemExit(0 if ok else 2)
