#!/usr/bin/env python3
import argparse,json,pathlib,sys

ap=argparse.ArgumentParser()
ap.add_argument("--candidate",required=True)
ap.add_argument("--out",required=True)
ap.add_argument("--min-independent-domains",type=int,default=2)
ap.add_argument("witnesses",nargs="+")
a=ap.parse_args()

accepted={}
domains={}
rejected=[]

for name in a.witnesses:
    p=pathlib.Path(name)
    if not p.is_file():
        rejected.append({"path":name,"reason":"missing_file"})
        continue
    d=json.loads(p.read_text())
    provider=d.get("provider")
    domain=d.get("failure_domain")
    if d.get("candidate_sha")!=a.candidate:
        rejected.append({"path":name,"reason":"candidate_mismatch"})
        continue
    if d.get("result")!="PASS":
        rejected.append({"path":name,"reason":"result_not_pass"})
        continue
    if not d.get("independent_failure_domain"):
        rejected.append({"path":name,"reason":"not_independent"})
        continue
    if not provider or not domain:
        rejected.append({"path":name,"reason":"identity_incomplete"})
        continue
    accepted[provider]=d
    domains.setdefault(domain,[]).append(provider)

independent_domains=sorted(domains)
quorum_pass=len(independent_domains)>=a.min_independent_domains

result={
    "schema_version":2,
    "candidate_sha":a.candidate,
    "provider_neutral":True,
    "required_minimum_independent_domains":a.min_independent_domains,
    "accepted_providers":sorted(accepted),
    "accepted_failure_domains":independent_domains,
    "real_witness_quorum":"PASS" if quorum_pass else "NOT_PROVEN",
    "rejected":rejected,
    "constitutional_promotion":"NOT_PROVEN"
}
pathlib.Path(a.out).write_text(json.dumps(result,indent=2)+"\n")

if not quorum_pass:
    print(
        "REAL_WITNESS_QUORUM=NOT_PROVEN "
        f"independent_domains={len(independent_domains)}/"
        f"{a.min_independent_domains}"
    )
    sys.exit(1)

print("REAL_WITNESS_QUORUM=PASS")
print("PROVIDER_NEUTRAL_QUORUM=PASS")
print("APPROVE_FOR_CONSTITUTION=NOT_PROVEN")
