#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2];GATE=ROOT/"scripts/policy/full_constitutional_gate.py";MATRIX=ROOT/"policy/provider_failure_domains.json"
def H(s):return hashlib.sha256(s.encode()).hexdigest()
def manifest():
 c="a"*40;b="b"*40
 return {"candidate_sha":c,"baseline_sha":b,"benchmarks":{k:{"candidate_sha":c,"passed":True} for k in ("contract_tests","regression_tests","adversarial_eval")},"evidence_ledger":[{"kind":"gate-self-test","sha256":H("x"),"source":"self-test"}],"rollback":{"target_sha":b,"tested":True},"independent_verifier":{"passed":True},"promotion_authority":{"requested":True}}
def run(m):
 with tempfile.NamedTemporaryFile("w",suffix=".json",delete=False) as f:json.dump(m,f);p=f.name
 r=subprocess.run([sys.executable,str(GATE),"--evidence",p],cwd=ROOT,text=True,capture_output=True);pathlib.Path(p).unlink(missing_ok=True);return r
prod=run(manifest())
if prod.returncode==0:raise SystemExit("production matrix unexpectedly allowed unverified routes")
print("PRODUCTION_UNVERIFIED_ROUTE_PATH=DENY")
original=MATRIX.read_text();data=json.loads(original)
try:
 for r in data["routes"]:r["verified"]=True
 MATRIX.write_text(json.dumps(data))
 ok=run(manifest())
 if ok.returncode!=0 or "PROMOTION_AUTHORITY=ALLOW" not in ok.stdout:print(ok.stdout);raise SystemExit("verified positive path failed")
 bad=manifest();bad["benchmarks"]["regression_tests"]["passed"]=False
 deny=run(bad)
 if deny.returncode==0 or "PROMOTION_AUTHORITY=ALLOW" in deny.stdout:raise SystemExit("regression failed open")
 print("VERIFIED_POSITIVE_PATH=ALLOW");print("NEGATIVE_REGRESSION_PATH=DENY")
finally:MATRIX.write_text(original)
