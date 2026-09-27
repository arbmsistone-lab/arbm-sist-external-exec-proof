#!/usr/bin/env python3
import json, os, pathlib, sys

ROOT=pathlib.Path(__file__).resolve().parents[2]
POLICY=ROOT/"policy"/"arbm_sist_constitution.json"
CONSTITUTION=ROOT/"docs"/"ARBM_SIST_TECHNICAL_CONSTITUTION.md"

def fail(msg):
    print("CONSTITUTION_GATE=FAIL", msg)
    raise SystemExit(1)

if not POLICY.is_file(): fail("policy_missing")
if not CONSTITUTION.is_file(): fail("constitution_missing")
p=json.loads(POLICY.read_text(encoding="utf-8"))
if p.get("fail_closed") is not True: fail("fail_closed_disabled")
if p.get("zero_spend") is not True: fail("zero_spend_disabled")

required={
"NO_SPOF","MULTI_PROVIDER_BY_CAPABILITY","ZERO_SPEND","CONTINUOUS_EVOLUTION",
"ZERO_UNDETECTED_REGRESSION","EVIDENCE_BEFORE_GREEN","INDEPENDENT_VERIFICATION",
"DURABLE_PORTABLE_STATE","TRANSACTIONAL_EFFECTS","VERSIONED_ROLLBACK",
"QUALITY_IS_MEASURED","FAIL_CLOSED_RELEASE"}
actual=set(p.get("protected_invariants",[]))
missing=sorted(required-actual)
if missing: fail("missing_invariants="+",".join(missing))

for name,cfg in p.get("critical_capabilities",{}).items():
    n=cfg.get("minimum_independent_routes")
    if not isinstance(n,int) or n<2: fail("provider_independence_underdefined:"+name)

ev=set(p.get("promotion_required_evidence",[]))
needed={"candidate_sha","baseline_sha","contract_tests","regression_tests","adversarial_eval",
        "provider_independence","zero_spend","rollback_target"}
if needed-ev: fail("promotion_evidence_incomplete")

# Runtime promotion mode is deliberately fail-closed: a release gate must supply
# an evidence manifest bound to exact candidate/baseline SHAs.
manifest=os.getenv("ARBM_PROMOTION_EVIDENCE")
if manifest:
    path=pathlib.Path(manifest)
    if not path.is_file(): fail("evidence_manifest_missing")
    m=json.loads(path.read_text(encoding="utf-8"))
    for k in needed:
        if k not in m: fail("evidence_field_missing:"+k)
    if not m["candidate_sha"] or not m["baseline_sha"]: fail("sha_binding_missing")
    for k in ("contract_tests","regression_tests","adversarial_eval","provider_independence","zero_spend"):
        if m[k] is not True: fail("promotion_gate_not_green:"+k)
    if not m["rollback_target"]: fail("rollback_target_missing")
    print("PROMOTION_AUTHORITY=PASS")
else:
    print("PROMOTION_AUTHORITY=NOT_EVALUATED (policy lint only)")

print("CONSTITUTION_GATE=PASS")
