#!/usr/bin/env python3
import json, pathlib, sys
from resilience_model import Route, Mission, independent_domains, survives
ROOT=pathlib.Path(__file__).resolve().parents[2]

def fail(msg):
    print("SOVEREIGN_RUNTIME_GATE=FAIL",msg); raise SystemExit(1)

def main():
    policy=json.loads((ROOT/"policy/sovereign_runtime_candidate.json").read_text())
    matrix=json.loads((ROOT/"policy/chaos_matrix_sovereign_runtime.json").read_text())
    if policy.get("status")!="candidate_not_constitutional": fail("candidate_status")
    if len(matrix.get("required_scenarios",[]))<16: fail("chaos_matrix_incomplete")

    now=1000
    routes=[
      Route("a","compute_execute","A",{"net-a"},witness_epoch=now),
      Route("b","compute_execute","B",{"net-b"},witness_epoch=now),
      Route("c","compute_execute","C",{"net-c"},witness_epoch=now),
      Route("d","compute_execute","D",{"net-d"},witness_epoch=now),
      Route("e","compute_execute","E",{"net-e"},witness_epoch=now),
    ]
    if independent_domains(routes,"compute_execute",now)<5: fail("insufficient_independent_compute")
    for lost in ({"A"},{"A","B"}):
        if not survives(routes,"compute_execute",now,lost,3): fail("two_fault_budget")

    expired=Route("stale","compute_execute","S",witness_epoch=0,witness_ttl=10)
    if expired.counts(now): fail("stale_route_counted")

    shared=[
      Route("x","compute_execute","X",{"shared-gateway"},witness_epoch=now),
      Route("y","compute_execute","Y",{"shared-gateway"},witness_epoch=now)]
    if independent_domains(shared,"compute_execute",now)!=1: fail("hidden_dependency_not_collapsed")

    m=Mission("m1","runtime-a",1010)
    try: m.takeover("runtime-b",1005); fail("premature_takeover")
    except RuntimeError as e:
        if str(e)!="LEASE_ACTIVE": raise
    token=m.takeover("runtime-b",1011)
    try: m.checkpoint_write("runtime-a",1,2); fail("stale_commit_accepted")
    except RuntimeError as e:
        if str(e)!="STALE_FENCE": raise
    m.checkpoint_write("runtime-b",token,2)
    duplicate=m.reconcile_effect("payment:42","provider_tx_9")
    if duplicate: fail("first_effect_seen_duplicate")
    if not m.reconcile_effect("payment:42","provider_tx_9"): fail("duplicate_not_reconciled")
    try: m.reconcile_effect("payment:42","provider_tx_OTHER"); fail("idempotency_conflict_accepted")
    except RuntimeError as e:
        if str(e)!="IDEMPOTENCY_CONFLICT": raise

    evidence={"schema_version":1,"candidate_status":"CANDIDATE","tests":{
      "lease_fencing_takeover":"PASS","qualification_ttl":"PASS",
      "dependency_collapse":"PASS","two_failure_domain_budget":"PASS",
      "idempotency_reconciliation":"PASS","chaos_matrix_contract":"PASS"}}
    out=ROOT/"evidence/sovereign-runtime"
    out.mkdir(parents=True,exist_ok=True)
    (out/"gate-result.json").write_text(json.dumps(evidence,indent=2)+"\n")
    print("SOVEREIGN_RUNTIME_GATE=PASS")
    print("CONSTITUTIONAL_PROMOTION=NOT_YET_AUTHORIZED")

if __name__=="__main__": main()
