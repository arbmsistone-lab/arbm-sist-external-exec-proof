# evolution-seed-ci-trigger-v2
#!/usr/bin/env python3
import json,pathlib,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[2]
tests=[
("constitution_policy",[sys.executable,"scripts/policy/constitution_gate.py"]),
("constitutional_adversarial",[sys.executable,"scripts/policy/test_full_constitutional_gate.py"]),
("context_isolation",[sys.executable,"arbm-context-isolation.py"]),
("control_isolation",[sys.executable,"arbm-control-isolation-tests.py"]),
("evidence_faults",[sys.executable,"arbm-evidence-fault-tests.py"]),
("shared_control",[sys.executable,"test_shared_control.py"]),
]
out=[]
for name,cmd in tests:
 t=time.monotonic();r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=180)
 out.append({"name":name,"passed":r.returncode==0,"seconds":round(time.monotonic()-t,3),"stdout_tail":r.stdout[-1200:],"stderr_tail":r.stderr[-1200:]})
report={"schema_version":1,"kind":"generalist_evolution_seed","tests":out,"passed":all(x["passed"] for x in out),"total":len(out),"passed_count":sum(x["passed"] for x in out)}
p=ROOT/"evidence/evolution/generalist-seed.json";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({"passed":report["passed"],"passed_count":report["passed_count"],"total":report["total"]}))
sys.exit(0 if report["passed"] else 1)
