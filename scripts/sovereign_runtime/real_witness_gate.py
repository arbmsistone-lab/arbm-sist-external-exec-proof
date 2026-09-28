#!/usr/bin/env python3
import argparse,json,pathlib,sys
ap=argparse.ArgumentParser()
ap.add_argument("--candidate",required=True)
ap.add_argument("--out",required=True)
ap.add_argument("witnesses",nargs="+")
a=ap.parse_args()
required={"github","circleci"}
seen={}
for name in a.witnesses:
 p=pathlib.Path(name)
 if not p.is_file(): continue
 d=json.loads(p.read_text())
 provider=d.get("provider")
 if d.get("candidate_sha")!=a.candidate: continue
 if d.get("result")!="PASS": continue
 if not d.get("independent_failure_domain"): continue
 seen[provider]=d
missing=required-set(seen)
result={
 "schema_version":1,"candidate_sha":a.candidate,
 "required_providers":sorted(required),"accepted_providers":sorted(seen),
 "real_witness_quorum":"PASS" if not missing else "NOT_PROVEN",
 "missing":sorted(missing),
 "constitutional_promotion":"NOT_PROVEN"
}
pathlib.Path(a.out).write_text(json.dumps(result,indent=2)+"\n")
if missing:
 print("REAL_WITNESS_QUORUM=NOT_PROVEN missing="+",".join(sorted(missing)));sys.exit(1)
print("REAL_WITNESS_QUORUM=PASS")
print("APPROVE_FOR_CONSTITUTION=NOT_PROVEN")
