#!/usr/bin/env python3
import json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
req=["formal_spec","threat_model","failure_domain_graph","chaos_matrix","adversarial_review","regression_suite","rollback_evidence"]
def main():
 p=json.loads((ROOT/"policy/sovereign_runtime_candidate.json").read_text())
 missing=[x for x in req if x not in p.get("promotion_required",[])]
 if missing: print("PROMOTION=FAIL missing_contract",missing); return 1
 e=ROOT/"evidence/sovereign-runtime/gate-result.json"
 if not e.exists(): print("PROMOTION=NOT_PROVEN missing_gate_evidence"); return 1
 d=json.loads(e.read_text())
 if any(v!="PASS" for v in d.get("tests",{}).values()): print("PROMOTION=NOT_PROVEN failed_gate"); return 1
 # Intentionally fail closed: synthetic model tests cannot constitutionalize the architecture.
 print("ADVERSARIAL_PROMOTION=CANDIDATE_READY_FOR_REAL_WITNESSES")
 print("APPROVE_FOR_CONSTITUTION=NOT_PROVEN")
 return 0
if __name__=="__main__": raise SystemExit(main())
