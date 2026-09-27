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
# Always prove fail-closed by temporarily removing one required verified source-control route.
original=MATRIX.read_text();data=json.loads(original)
try:
 candidates=[r for r in data["routes"] if "source_control" in r.get("capabilities",[]) and r.get("verified") is True]
 if len(candidates)<2: raise SystemExit("production matrix lacks required verified source-control routes")
 candidates[-1]["verified"]=False
 MATRIX.write_text(json.dumps(data))
 deny_missing=run(manifest())
 if deny_missing.returncode==0:raise SystemExit("missing-route mutation failed open")
 print("MUTATED_MISSING_ROUTE_PATH=DENY")
finally:MATRIX.write_text(original)
# Current production matrix must ALLOW a complete synthetic logic fixture.
ok=run(manifest())
if ok.returncode!=0 or "PROMOTION_AUTHORITY=ALLOW" not in ok.stdout:print(ok.stdout);raise SystemExit("verified positive path failed")
bad=manifest();bad["benchmarks"]["regression_tests"]["passed"]=False
deny=run(bad)
if deny.returncode==0 or "PROMOTION_AUTHORITY=ALLOW" in deny.stdout:raise SystemExit("regression failed open")
print("VERIFIED_POSITIVE_PATH=ALLOW");print("NEGATIVE_REGRESSION_PATH=DENY")
