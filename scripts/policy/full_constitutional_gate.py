#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def fail(x): print("FULL_CONSTITUTIONAL_ENFORCEMENT=FAIL",x); sys.exit(1)
def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--evidence",required=True); a=ap.parse_args()
 policy=load("policy/arbm_sist_constitution.json"); matrix=load("policy/provider_failure_domains.json"); bench=load("policy/benchmark_contract.json")
 e=json.loads(pathlib.Path(a.evidence).read_text(encoding="utf-8"))
 if not policy.get("fail_closed"): fail("fail_closed_disabled")
 cand=e.get("candidate_sha"); base=e.get("baseline_sha")
 if not cand or not base or cand==base: fail("invalid_sha_binding")
 for suite in bench["required_suites"]:
  s=e.get("benchmarks",{}).get(suite,{})
  if s.get("candidate_sha")!=cand or s.get("passed") is not True: fail("benchmark:"+suite)
 routes=matrix["routes"]
 for cap,cfg in policy["critical_capabilities"].items():
  domains={r["failure_domain"] for r in routes if cap in r["capabilities"] and r.get("verified") is not False}
  if len(domains)<cfg["minimum_independent_routes"]: fail("failure_domains:"+cap)
 if any(r.get("cost_class")!="free" for r in routes): fail("zero_spend")
 ledger=e.get("evidence_ledger",[])
 if not ledger: fail("evidence_ledger_empty")
 for item in ledger:
  if not all(item.get(k) for k in ("kind","sha256","source")): fail("ledger_record_incomplete")
  if len(item["sha256"])!=64: fail("ledger_hash_invalid")
 rb=e.get("rollback",{})
 if rb.get("target_sha")!=base or rb.get("tested") is not True: fail("rollback_unproven")
 if e.get("independent_verifier",{}).get("passed") is not True: fail("independent_verifier")
 if e.get("promotion_authority",{}).get("requested") is not True: fail("promotion_not_requested")
 print("PROMOTION_AUTHORITY=ALLOW")
 print("FULL_CONSTITUTIONAL_ENFORCEMENT=PASS")
if __name__=="__main__": main()
