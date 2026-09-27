#!/usr/bin/env python3
import argparse,hashlib,json,pathlib
def sha256(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
ap=argparse.ArgumentParser()
ap.add_argument("--candidate-sha",required=True);ap.add_argument("--baseline-sha",required=True)
ap.add_argument("--out",default="evidence/constitutional/promotion-evidence.json")
ap.add_argument("--evidence",action="append",default=[],help="kind:path:source")
ap.add_argument("--contract-pass",action="store_true");ap.add_argument("--regression-pass",action="store_true");ap.add_argument("--adversarial-pass",action="store_true")
ap.add_argument("--rollback-tested",action="store_true");ap.add_argument("--independent-verifier-pass",action="store_true")
a=ap.parse_args(); ledger=[]
for spec in a.evidence:
 kind,path,source=spec.split(":",2);p=pathlib.Path(path)
 if not p.is_file():raise SystemExit("missing evidence: "+path)
 ledger.append({"kind":kind,"sha256":sha256(p),"source":source,"path":path,"bytes":p.stat().st_size})
m={"candidate_sha":a.candidate_sha,"baseline_sha":a.baseline_sha,
"benchmarks":{"contract_tests":{"candidate_sha":a.candidate_sha,"passed":a.contract_pass},"regression_tests":{"candidate_sha":a.candidate_sha,"passed":a.regression_pass},"adversarial_eval":{"candidate_sha":a.candidate_sha,"passed":a.adversarial_pass}},
"evidence_ledger":ledger,"rollback":{"target_sha":a.baseline_sha,"tested":a.rollback_tested},
"independent_verifier":{"passed":a.independent_verifier_pass},"promotion_authority":{"requested":True}}
out=pathlib.Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(m,indent=2)+"\n")
print("EVIDENCE_LEDGER_RECORDS="+str(len(ledger)));print("PROMOTION_MANIFEST="+str(out))
