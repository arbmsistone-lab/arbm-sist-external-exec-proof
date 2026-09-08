"""Build immutable ARBM SIST Top-3 evidence pack metadata."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "top3-certification-manifest.json"
GATE = ROOT / "top3-certification-gate.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    import importlib.util
    spec = importlib.util.spec_from_file_location("top3_gate", GATE)
    gate = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(gate)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    result = gate.certify(MANIFEST)
    gates = manifest.get("gates") or {}
    evidence = {}
    for name, data in gates.items():
        if not isinstance(data, dict):
            continue
        evidence[name] = {k: v for k, v in data.items() if k in {"status", "run_id", "job_id", "artifact_id", "artifact_digest", "proof_digest"}}
    pack = {
        "schema": "arbm-sist-top3-evidence-pack-v1",
        "candidateSha": manifest.get("candidate_sha"),
        "manifestSha256": sha256(MANIFEST),
        "gateScriptSha256": sha256(GATE),
        "mandatoryCostUsd": manifest.get("mandatory_cost_usd"),
        "top3Certified": result["top3Certified"],
        "failures": result["failures"],
        "evidence": evidence,
    }
    out = ROOT / "top3-evidence-pack.json"
    out.write_text(json.dumps(pack, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(pack, sort_keys=True))
    return 0 if pack["top3Certified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
