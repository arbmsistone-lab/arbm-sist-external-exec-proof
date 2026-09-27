#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,sys
ap=argparse.ArgumentParser();ap.add_argument("--candidate",required=True);ap.add_argument("--baseline",required=True);ap.add_argument("--constitutional-run",required=True);ap.add_argument("--adversarial-run",required=True);ap.add_argument("--witness-run",required=True);ap.add_argument("--witness-json",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
def load(p):return json.loads(pathlib.Path(p).read_text())
def H(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
runs=[load(a.constitutional_run),load(a.adversarial_run),load(a.witness_run)]
for r in runs:
 if r.get("head_sha")!=a.candidate or r.get("conclusion")!="success":raise SystemExit("run binding/conclusion failure")
w=load(a.witness_json)
if w.get("candidate_sha")!=a.candidate or w.get("baseline_sha")!=a.baseline:raise SystemExit("witness binding failure")
if w["regression_tests"].get("passed") is not True or w["rollback"].get("tested") is not True or w["independent_verifier"].get("passed") is not True:raise SystemExit("witness not green")
ledger=[]
for kind,p in zip(("contract_tests","adversarial_eval","witness_executor"),(a.constitutional_run,a.adversarial_run,a.witness_run)):
 d=load(p);ledger.append({"kind":kind,"sha256":H(p),"source":"github_actions","run_id":d["id"],"candidate_sha":a.candidate})
ledger.append({"kind":"real_witness_artifact","sha256":H(a.witness_json),"source":"github_actions_artifact","candidate_sha":a.candidate})
m={"candidate_sha":a.candidate,"baseline_sha":a.baseline,
"benchmarks":{"contract_tests":{"candidate_sha":a.candidate,"passed":True},"regression_tests":{"candidate_sha":a.candidate,"passed":True},"adversarial_eval":{"candidate_sha":a.candidate,"passed":True}},
"evidence_ledger":ledger,"rollback":{"target_sha":a.baseline,"tested":True},"independent_verifier":{"passed":True},"promotion_authority":{"requested":True}}
pathlib.Path(a.out).write_text(json.dumps(m,indent=2)+"\n");print("REAL_PROMOTION_MANIFEST=BUILT")
