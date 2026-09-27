#!/usr/bin/env python3
import hashlib, json, pathlib, subprocess, sys, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
GATE=ROOT/"scripts/policy/full_constitutional_gate.py"
def h(x): return hashlib.sha256(x.encode()).hexdigest()
def manifest(good=True):
 c="a"*40; b="b"*40
 m={"candidate_sha":c,"baseline_sha":b,
 "benchmarks":{k:{"candidate_sha":c,"passed":True} for k in ("contract_tests","regression_tests","adversarial_eval")},
 "evidence_ledger":[{"kind":"synthetic-gate-test","sha256":h("constitutional-test"),"source":"self-test"}],
 "rollback":{"target_sha":b,"tested":True},"independent_verifier":{"passed":True},"promotion_authority":{"requested":True}}
 if not good: m["benchmarks"]["regression_tests"]["passed"]=False
 return m
def run(m):
 with tempfile.NamedTemporaryFile("w",suffix=".json",delete=False) as f: json.dump(m,f); p=f.name
 r=subprocess.run([sys.executable,str(GATE),"--evidence",p],cwd=ROOT,text=True,capture_output=True)
 pathlib.Path(p).unlink(missing_ok=True); return r
ok=run(manifest(True))
if ok.returncode!=0 or "PROMOTION_AUTHORITY=ALLOW" not in ok.stdout: print(ok.stdout,ok.stderr); raise SystemExit("positive path failed")
bad=run(manifest(False))
if bad.returncode==0 or "PROMOTION_AUTHORITY=ALLOW" in bad.stdout: print(bad.stdout,bad.stderr); raise SystemExit("tamper/regression path failed open")
print("CONSTITUTION_POSITIVE_PATH=PASS")
print("CONSTITUTION_NEGATIVE_REGRESSION_PATH=DENY")
