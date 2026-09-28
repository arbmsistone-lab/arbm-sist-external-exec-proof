#!/usr/bin/env python3
import argparse, json, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[2]

def load(p):
    return json.loads((ROOT/p).read_text(encoding="utf-8"))

def fail(x):
    print("FULL_CONSTITUTIONAL_ENFORCEMENT=FAIL",x)
    sys.exit(1)

def valid_hash(x):
    if not isinstance(x,str) or len(x)!=64:
        return False
    try:
        int(x,16)
        return True
    except ValueError:
        return False

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--evidence",required=True)
    a=ap.parse_args()
    policy=load("policy/arbm_sist_constitution.json")
    matrix=load("policy/provider_failure_domains.json")
    bench=load("policy/benchmark_contract.json")
    e=json.loads(pathlib.Path(a.evidence).read_text(encoding="utf-8"))

    if not policy.get("fail_closed"):
        fail("fail_closed_disabled")

    cand=e.get("candidate_sha")
    base=e.get("baseline_sha")
    if not cand or not base or cand==base or len(cand)!=40 or len(base)!=40:
        fail("invalid_sha_binding")

    for suite in bench["required_suites"]:
        s=e.get("benchmarks",{}).get(suite,{})
        if s.get("candidate_sha")!=cand or s.get("passed") is not True:
            fail("benchmark:"+suite)

    routes=matrix["routes"]
    for cap,cfg in policy["critical_capabilities"].items():
        domains={
            r["failure_domain"] for r in routes
            if cap in r["capabilities"] and r.get("verified") is not False
        }
        if len(domains)<cfg["minimum_independent_routes"]:
            fail("failure_domains:"+cap)

    if any(r.get("cost_class")!="free" for r in routes):
        fail("zero_spend")

    # Candidate execution independence must be proven dynamically, never inherited
    # from a stale static verified=true route in the policy matrix.
    declared_compute={
        r["failure_domain"] for r in routes
        if "compute_execute" in r.get("capabilities",[])
        and r.get("verified") is not False
        and r.get("cost_class")=="free"
    }
    compute_witnesses=e.get("compute_witnesses",[])
    exact_domains=set()
    for w in compute_witnesses:
        if w.get("candidate_sha")!=cand:
            fail("compute_witness_candidate_mismatch")
        if w.get("result")!="PASS" or w.get("independent_failure_domain") is not True:
            fail("compute_witness_not_proven")
        if w.get("cost_class")!="free":
            fail("compute_witness_not_zero_spend")
        if w.get("failure_domain") not in declared_compute:
            fail("compute_witness_undeclared_domain")
        if not valid_hash(w.get("sha256")):
            fail("compute_witness_hash_invalid")
        exact_domains.add(w["failure_domain"])
    need=policy["critical_capabilities"]["compute_execute"]["minimum_independent_routes"]
    if len(exact_domains)<need:
        fail("exact_candidate_compute_quorum")

    ledger=e.get("evidence_ledger",[])
    if not ledger:
        fail("evidence_ledger_empty")
    for item in ledger:
        if not all(item.get(k) for k in ("kind","sha256","source")):
            fail("ledger_record_incomplete")
        if not valid_hash(item["sha256"]):
            fail("ledger_hash_invalid")

    rb=e.get("rollback",{})
    if rb.get("target_sha")!=base or rb.get("tested") is not True:
        fail("rollback_unproven")

    if e.get("independent_verifier",{}).get("passed") is not True:
        fail("independent_verifier")
    if e.get("promotion_authority",{}).get("requested") is not True:
        fail("promotion_not_requested")

    print("EXACT_CANDIDATE_COMPUTE_QUORUM=PASS")
    print("PROMOTION_AUTHORITY=ALLOW")
    print("FULL_CONSTITUTIONAL_ENFORCEMENT=PASS")

if __name__=="__main__":
    main()
