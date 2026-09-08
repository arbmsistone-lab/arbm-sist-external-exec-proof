"""Fail-closed ARBM SIST Top 3 certification gate."""
from __future__ import annotations
import json
from pathlib import Path
import sys

REQUIRED_GATES = (
    "official_engineering_evaluator",
    "terminal_benchmark",
    "computer_use_benchmark",
    "ai_three_independent_providers",
    "three_independent_runners",
    "distributed_recovery",
    "remote_cancel_preempt",
    "context_isolation",
    "long_missions",
    "universal_evidence_pack",
)


def validate_manifest(manifest: dict) -> list[str]:
    failures: list[str] = []
    if manifest.get("schema") != "arbm-sist-top3-certification-v1":
        failures.append("schema")
    if manifest.get("policy") != "fail-closed":
        failures.append("policy")
    if manifest.get("mandatory_cost_usd") != 0:
        failures.append("mandatory_cost_usd")
    gates = manifest.get("gates") or {}
    for name in REQUIRED_GATES:
        gate = gates.get(name)
        if not isinstance(gate, dict):
            failures.append(f"missing_gate:{name}")
            continue
        if gate.get("status") != "PASS":
            failures.append(f"gate_not_pass:{name}:{gate.get('status')}")

    engineering = gates.get("official_engineering_evaluator") or {}
    if engineering.get("resolved") is not True:
        failures.append("engineering_resolved")
    if engineering.get("pass_to_pass") != "6954/6954":
        failures.append("engineering_pass_to_pass")
    if engineering.get("none_to_pass") != "1/1":
        failures.append("engineering_none_to_pass")
    if engineering.get("fail_closed") is not True:
        failures.append("engineering_fail_closed")
    digest = str(engineering.get("artifact_digest") or "")
    if not digest.startswith("sha256:") or len(digest) != 71:
        failures.append("engineering_artifact_digest")

    ai = gates.get("ai_three_independent_providers") or {}
    if ai.get("status") == "PASS":
        if ai.get("independent_providers") != 3:
            failures.append("ai_independent_provider_count")
        providers = ai.get("providers") or []
        if len(set(providers)) != 3:
            failures.append("ai_provider_identity")
        if ai.get("mandatory_cost_usd") != 0:
            failures.append("ai_mandatory_cost_usd")
        if ai.get("fail_closed") is not True:
            failures.append("ai_fail_closed")
        ai_digest = str(ai.get("artifact_digest") or "")
        if not ai_digest.startswith("sha256:") or len(ai_digest) != 71:
            failures.append("ai_artifact_digest")
        if not isinstance(ai.get("proof_run_id"), int) or not isinstance(ai.get("artifact_id"), int):
            failures.append("ai_proof_ids")
    return failures


def certify(path: Path) -> dict:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    failures = validate_manifest(manifest)
    return {
        "top3Certified": not failures,
        "candidateSha": manifest.get("candidate_sha"),
        "failures": failures,
    }


if __name__ == "__main__":
    result = certify(Path(sys.argv[1]))
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(0 if result["top3Certified"] else 1)
