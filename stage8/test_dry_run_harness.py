from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"stage8"))
from dry_run_harness import run_adapter
PY=r"C:\Users\airto\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
adapter=[PY,str(ROOT/"stage8"/"dummy_adapter.py")]
ok=0
for i in range(1,4):
    task=ROOT/"stage8"/"dev_tasks"/f"dev_task_0{i}.json"
    out=ROOT/"stage8"/"runs"/f"dummy_dev_0{i}"
    r=run_adapter(adapter,task,out)
    good=(r["returncode"]==0 and '"paid_cost_usd": 0.0' in r["stdout"] and '"model_calls": 0' in r["stdout"])
    ok+=int(good)
    print(f"DEV_DRY_{i:02d}={'PASS' if good else 'FAIL'}")
print(f"DRY_RUN_HARNESS_CASES={ok}/3")
print("MODEL_CALLS_EXECUTED=0")
print("PAID_COST_USD=0.00")
print("STAGE8_HARNESS_PREP=PASS" if ok==3 else "STAGE8_HARNESS_PREP=FAIL")
raise SystemExit(0 if ok==3 else 1)
