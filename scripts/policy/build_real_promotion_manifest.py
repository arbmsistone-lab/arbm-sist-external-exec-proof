#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,sys
ap=argparse.ArgumentParser();ap.add_argument("--candidate-sha",required=True);ap.add_argument("--baseline-sha",required=True);ap.add_argument("--run",action="append",default=[]);ap.add_argument("--out",required=True);a=ap.parse_args()
if not a.run: raise SystemExit("no real runs supplied")
ledger=[]; seen=set()
for spec in a.run:
 p=pathlib.Path(spec)
 d=json.loads(p.read_text())
 if d.get("head_sha")!=a.candidate_sha: raise SystemExit("candidate mismatch:"+spec)
 if d.get("conclusion")!="success": raise SystemExit("non-success run:"+spec)
 raw=p.read_bytes(); h=hashlib.sha256(raw).hexdigest()
 name=d.get("name","")
 kind=("adversarial_eval" if "Adversarial" in name else "contract_tests" if "Constitutional Gate" in name else "executor_run")
 ledger.append({"kind":kind,"sha256":h,"source":"github_actions","run_id":d.get("id"),"workflow":name,"candidate_sha":a.candidate_sha})
 seen.add(kind)
bench={k:{"candidate_sha":a.candidate_sha,"passed":k in seen,"source":"real_run"} for k in ("contract_tests","regression_tests","adversarial_eval")}
# Regression remains false until a dedicated real regression executor is connected.
m={"candidate_sha":a.candidate_sha,"baseline_sha":a.baseline_sha,"benchmarks":bench,"evidence_ledger":ledger,"rollback":{"target_sha":a.baseline_sha,"tested":False},"independent_verifier":{"passed":False},"promotion_authority":{"requested":True}}
pathlib.Path(a.out).write_text(json.dumps(m,indent=2)+"\n")
print("REAL_LEDGER_RECORDS",len(ledger));print("REAL_KINDS",sorted(seen));print("PROMOTION_EXPECTED","DENY")
