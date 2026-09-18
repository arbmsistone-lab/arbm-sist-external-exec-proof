"""Fail-closed validator for MASTER SUPREME assurance ledger."""
import json
import re
from pathlib import Path

ALLOWED={"PASS","FAIL","BLOCKED","NOT_APPLICABLE"}
SHA40=re.compile(r"^[0-9a-f]{40}$")


def validate_registry(data):
    errors=[]
    rc=data.get("release_candidate") or {}
    sha=str(rc.get("sha") or "")
    if not SHA40.fullmatch(sha):
        errors.append("RC_SHA_INVALID")
    if rc.get("immutable_during_proof") is not True:
        errors.append("RC_NOT_FROZEN")
    if set(data.get("allowed_states") or []) != ALLOWED:
        errors.append("STATE_ENUM_MISMATCH")

    gates=data.get("gates")
    if not isinstance(gates,list) or not gates:
        return ["GATES_MISSING"]
    by_id={}
    for g in gates:
        gid=str(g.get("id") or "")
        if not gid or gid in by_id:
            errors.append("GATE_ID_INVALID_OR_DUPLICATE:"+gid)
            continue
        by_id[gid]=g
        state=g.get("state")
        if state not in ALLOWED:
            errors.append("GATE_STATE_INVALID:"+gid)
        if state=="PASS" and not str(g.get("evidence") or "").strip():
            errors.append("PASS_WITHOUT_EVIDENCE:"+gid)
        if state=="BLOCKED" and not str(g.get("cause") or "").strip():
            errors.append("BLOCKED_WITHOUT_CAUSE:"+gid)
        if state=="FAIL" and not str(g.get("remediation") or "").strip():
            errors.append("FAIL_WITHOUT_REMEDIATION:"+gid)
        if state=="NOT_APPLICABLE" and not str(g.get("justification") or "").strip():
            errors.append("NA_WITHOUT_JUSTIFICATION:"+gid)

    for gid,g in by_id.items():
        for dep in g.get("depends_on") or []:
            if dep not in by_id:
                errors.append("UNKNOWN_DEPENDENCY:"+gid+":"+str(dep))
            elif g.get("state")=="PASS" and by_id[dep].get("state")!="PASS":
                errors.append("PASS_WITH_UNMET_DEPENDENCY:"+gid+":"+str(dep))

    final=by_id.get("G-FINAL-SIGNOFF")
    if final and final.get("state")=="PASS":
        for gid,g in by_id.items():
            if gid=="G-FINAL-SIGNOFF":
                continue
            if g.get("state") not in ("PASS","NOT_APPLICABLE"):
                errors.append("FINAL_SIGNOFF_WITH_OPEN_GATE:"+gid)

    rules=data.get("rules") or {}
    required_rules=(
        "evidence_required_for_pass",
        "justification_required_for_not_applicable",
        "remediation_required_for_fail",
        "explicit_cause_required_for_blocked",
        "zero_false_green",
        "no_gate_bypass",
        "change_invalidates_affected_gates",
    )
    for key in required_rules:
        if rules.get(key) is not True:
            errors.append("RULE_DISABLED:"+key)
    return errors


def validate_manifest(data, registry):
    errors=[]
    rcsha=(registry.get("release_candidate") or {}).get("sha")
    if data.get("frozen_candidate_sha") != rcsha:
        errors.append("MANIFEST_RC_SHA_MISMATCH")
    entries=data.get("evidence")
    if not isinstance(entries,list) or not entries:
        errors.append("EVIDENCE_ENTRIES_MISSING")
        return errors
    for i,e in enumerate(entries):
        state=e.get("state")
        if state not in ALLOWED:
            errors.append(f"EVIDENCE_STATE_INVALID:{i}")
        if state=="PASS":
            if not str(e.get("evidence_reference") or "").strip():
                errors.append(f"EVIDENCE_PASS_WITHOUT_REFERENCE:{i}")
            if e.get("commit_sha") != rcsha:
                errors.append(f"EVIDENCE_PASS_SHA_MISMATCH:{i}")
    if data.get("certification_state")=="PASS":
        final=next((g for g in registry.get("gates",[]) if g.get("id")=="G-FINAL-SIGNOFF"),None)
        if not final or final.get("state")!="PASS":
            errors.append("CERTIFICATION_PASS_WITHOUT_FINAL_SIGNOFF")
    return errors


def main(root=Path(".")):
    registry=json.loads((root/"assurance/master-supreme/gate-registry.json").read_text())
    manifest=json.loads((root/"assurance/master-supreme/evidence-manifest.json").read_text())
    errors=validate_registry(registry)+validate_manifest(manifest,registry)
    if errors:
        raise SystemExit("MASTER_SUPREME_ASSURANCE_FAIL:"+json.dumps(errors,sort_keys=True))
    print(json.dumps({
        "status":"MASTER_SUPREME_ASSURANCE_LEDGER_VALID",
        "release_candidate_sha":registry["release_candidate"]["sha"],
        "final_signoff":next(g["state"] for g in registry["gates"] if g["id"]=="G-FINAL-SIGNOFF"),
        "open_gates":[g["id"] for g in registry["gates"] if g["state"] in ("FAIL","BLOCKED")],
    },sort_keys=True))


if __name__=="__main__":
    main()
