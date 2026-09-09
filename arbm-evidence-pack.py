from __future__ import annotations
import hashlib
import json
from pathlib import Path

REQUIRED = ("candidate_sha","mission_id","executor_provider","ai_provider","input_sha256","output_sha256","tests","mandatory_cost_usd","started_at","finished_at")


def validate_pack(data: dict) -> list[str]:
    failures=[]
    for key in REQUIRED:
        if key not in data or data[key] in (None, ""):
            failures.append("missing:"+key)
    if data.get("mandatory_cost_usd") != 0:
        failures.append("mandatory_cost_nonzero")
    tests=data.get("tests") or {}
    if tests.get("failed", 1) != 0 or tests.get("passed", 0) < 1:
        failures.append("tests_not_green")
    if len(str(data.get("input_sha256",""))) != 64:
        failures.append("input_hash_invalid")
    if len(str(data.get("output_sha256",""))) != 64:
        failures.append("output_hash_invalid")
    return failures

def freeze_pack(data: dict, root: Path) -> dict:
    failures=validate_pack(data)
    if failures:
        raise ValueError("EVIDENCE_PACK_INVALID:"+",".join(failures))
    root.mkdir(parents=True, exist_ok=True)
    payload=json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    digest=hashlib.sha256(payload).hexdigest()
    (root/"evidence-pack.json").write_bytes(payload)
    (root/"evidence-pack.sha256").write_text(digest+"  evidence-pack.json\n", encoding="utf-8")
    return {"sha256":digest,"bytes":len(payload)}
