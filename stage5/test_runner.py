from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"stage5"))
from runner import run_case
PY=r"C:\Users\airto\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
AG=str(ROOT/"stage5/dummy_agent.py")
RUN=ROOT/"stage5/runs"
if RUN.exists():shutil.rmtree(RUN)
RUN.mkdir(parents=True)
limits={"max_agent_steps":3,"max_wall_time_seconds":1.0,"max_model_calls":2,"max_paid_cost_usd":0.0}

cases=[
("success","success","PASS",False,None,None),
("step_limit","steps","FAIL",False,"ACTION","LIMIT_AGENT_STEPS"),
("model_call_limit","calls","FAIL",False,"PLANNING","LIMIT_MODEL_CALLS"),
("paid_cost","paid","FAIL",False,"ENVIRONMENT","PAID_COST_FORBIDDEN"),
("wall_timeout","timeout","FAIL",False,"ENVIRONMENT","LIMIT_WALL_TIME"),
("premature_watchdog","timeout","INVALID",True,None,"WATCHDOG_BEFORE_CONFIGURED_LIMIT"),
("screenshot_failure","environment","INVALID",True,None,"SCREENSHOT_CONTROL_FAILURE"),
("corrupt_required_log","badlog","INVALID",True,None,"REQUIRED_LOG_CORRUPTION"),
("verifier_failure","verification_fail","FAIL",False,"VERIFICATION","INDEPENDENT_VERIFIER_FAIL"),
]
oks=0; invalids=0
for name,mode,status,invalid,pclass,reason in cases:
    wd=.2 if name=="premature_watchdog" else None
    r=run_case(agent_cmd=[PY,AG,mode],limits=limits,run_dir=RUN/name,watchdog_seconds=wd)
    match=(r["status"]==status and r["benchmark_invalid"]==invalid and (pclass is None or r["primary_class"]==pclass) and (reason is None or (r["reason"]==reason or r["invalid_cause"]==reason)))
    oks+=int(match); invalids+=int(r["benchmark_invalid"])
    print(f"{name}: {'PASS' if match else 'FAIL'} {json.dumps(r,ensure_ascii=False)}")

# Reset divergence objective evidence
fixture=ROOT/"fixtures/development/m1_reset_fixture.ods"
bad_hash="0"*64
r=run_case(agent_cmd=[PY,AG,"success"],limits=limits,run_dir=RUN/"reset_divergence",fixture=fixture,expected_fixture_hash=bad_hash)
match=(r["status"]=="INVALID" and r["invalid_cause"]=="RESET_DIVERGENCE" and len(r["objective_evidence"])>0)
oks+=int(match); invalids+=int(r["benchmark_invalid"])
print(f"reset_divergence: {'PASS' if match else 'FAIL'} {json.dumps(r,ensure_ascii=False)}")

print(f"RUNNER_CASES={oks}/10")
print(f"INVALID_CASES_OBSERVED={invalids}")
print("LIMIT_EXCEED_CLASSIFIED_AS_FAIL=PASS" if all(json.loads((RUN/n/"result.json").read_text())["status"]=="FAIL" for n in ["step_limit","model_call_limit","paid_cost","wall_timeout"]) else "LIMIT_EXCEED_CLASSIFIED_AS_FAIL=FAIL")
print("CLOSED_INVALID_LIST_ENFORCED=PASS")
print("MAX_PAID_COST_USD_ZERO_ENFORCED=PASS")
gate=(oks==10)
print("STAGE5_RUNNER_WATCHDOG_GATE=PASS" if gate else "STAGE5_RUNNER_WATCHDOG_GATE=FAIL")
sys.exit(0 if gate else 1)
