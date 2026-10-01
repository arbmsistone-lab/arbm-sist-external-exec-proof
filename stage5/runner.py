from __future__ import annotations
from pathlib import Path
import subprocess,sys,time,json,threading,queue,hashlib

INVALID_CAUSES={
"RUNNER_BUG","RESET_DIVERGENCE","EVALUATOR_VERIFIER_BUG",
"WATCHDOG_BEFORE_CONFIGURED_LIMIT","SCREENSHOT_CONTROL_FAILURE",
"MACHINE_RESTART","SECRET_FIXTURE_UNAVAILABLE","REQUIRED_LOG_CORRUPTION"
}

def _hash_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for c in iter(lambda:f.read(65536),b""):h.update(c)
    return h.hexdigest()

def run_case(*,agent_cmd,limits,run_dir,watchdog_seconds=None,fixture=None,expected_fixture_hash=None):
    rd=Path(run_dir); rd.mkdir(parents=True,exist_ok=True)
    events_path=rd/"events.jsonl"; result_path=rd/"result.json"
    started=time.monotonic()
    res={"status":None,"primary_class":None,"reason":None,"benchmark_invalid":False,
         "invalid_cause":None,"steps":0,"model_calls":0,"paid_cost_usd":0.0,
         "configured_limits":limits,"watchdog_seconds":watchdog_seconds,
         "objective_evidence":[]}
    if fixture is not None and expected_fixture_hash is not None:
        actual=_hash_file(fixture)
        if actual!=expected_fixture_hash:
            res.update(status="INVALID",benchmark_invalid=True,invalid_cause="RESET_DIVERGENCE",reason="fixture hash mismatch")
            res["objective_evidence"].append({"fixture_hash_actual":actual,"fixture_hash_expected":expected_fixture_hash})
            result_path.write_text(json.dumps(res,indent=2),encoding="utf-8"); return res
    p=subprocess.Popen(agent_cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
    q=queue.Queue()
    def reader():
        try:
            for line in p.stdout:q.put(("line",line))
        finally:q.put(("eof",None))
    threading.Thread(target=reader,daemon=True).start()
    kill_reason=None; eof=False
    wd=watchdog_seconds if watchdog_seconds is not None else limits["max_wall_time_seconds"]
    with events_path.open("w",encoding="utf-8") as lf:
        while True:
            elapsed=time.monotonic()-started
            if elapsed>=wd and p.poll() is None:
                p.kill()
                if wd < limits["max_wall_time_seconds"]:
                    res.update(status="INVALID",benchmark_invalid=True,invalid_cause="WATCHDOG_BEFORE_CONFIGURED_LIMIT",reason="watchdog killed before configured wall limit")
                    res["objective_evidence"].append({"elapsed":elapsed,"watchdog":wd,"configured_wall":limits["max_wall_time_seconds"]})
                else:
                    res.update(status="FAIL",primary_class="ENVIRONMENT",reason="LIMIT_WALL_TIME")
                break
            try: typ,val=q.get(timeout=.05)
            except queue.Empty:
                if p.poll() is not None and eof:break
                continue
            if typ=="eof":
                eof=True
                if p.poll() is not None:break
                continue
            lf.write(val); lf.flush()
            try:ev=json.loads(val)
            except Exception:
                res.update(status="INVALID",benchmark_invalid=True,invalid_cause="REQUIRED_LOG_CORRUPTION",reason="non-json event")
                res["objective_evidence"].append({"bad_line":val.strip()}); p.kill(); break
            et=ev.get("type")
            if et=="step":
                res["steps"]+=1
                if res["steps"]>limits["max_agent_steps"]:
                    res.update(status="FAIL",primary_class="ACTION",reason="LIMIT_AGENT_STEPS"); p.kill(); break
            elif et=="model_call":
                res["model_calls"]+=1; res["paid_cost_usd"]+=float(ev.get("cost_usd",0.0))
                if res["model_calls"]>limits["max_model_calls"]:
                    res.update(status="FAIL",primary_class="PLANNING",reason="LIMIT_MODEL_CALLS"); p.kill(); break
                if res["paid_cost_usd"]>limits["max_paid_cost_usd"]:
                    res.update(status="FAIL",primary_class="ENVIRONMENT",reason="PAID_COST_FORBIDDEN"); p.kill(); break
            elif et=="environment_error":
                code=ev.get("code")
                if code=="SCREENSHOT_UNAVAILABLE":
                    res.update(status="INVALID",benchmark_invalid=True,invalid_cause="SCREENSHOT_CONTROL_FAILURE",reason=code)
                    res["objective_evidence"].append(ev); p.kill(); break
                res.update(status="FAIL",primary_class="ENVIRONMENT",reason=code); p.kill(); break
            elif et=="done":
                if ev.get("verifier")=="FAIL":
                    res.update(status="FAIL",primary_class="VERIFICATION",reason="INDEPENDENT_VERIFIER_FAIL")
                else:
                    res.update(status="PASS",primary_class=None,reason="DONE")
                break
        if p.poll() is None:p.kill()
        try:p.wait(timeout=2)
        except Exception:pass
    if res["status"] is None:
        if p.returncode==0:res.update(status="FAIL",primary_class="VERIFICATION",reason="NO_DONE_EVENT")
        else:res.update(status="FAIL",primary_class="ENVIRONMENT",reason=f"AGENT_EXIT_{p.returncode}")
    if res["benchmark_invalid"] and res["invalid_cause"] not in INVALID_CAUSES:
        raise RuntimeError("invalid cause outside closed list")
    result_path.write_text(json.dumps(res,indent=2),encoding="utf-8")
    return res

if __name__=="__main__":
    raise SystemExit("import runner.run_case")
