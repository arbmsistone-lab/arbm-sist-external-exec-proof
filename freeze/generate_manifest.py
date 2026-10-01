from __future__ import annotations
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parent.parent
TARGETS=[
 "PROTOCOLO_M1.md",
 "stage2/verifier_engine.py",
 "stage3/integrity_checker.py",
 "stage4/oracle_runner.py",
 "stage5/runner.py",
 "stage5/round_policy.py",
 "stage7/preflight.py",
 "stage7/baseline_agent.py",
 "stage7/baseline_config.template.json",
 "stage7/baseline_prompt.template.md",
 "stage8/dry_run_harness.py",
 "randomization/generate_order.py",
 "randomization/verify_order.py"
]
def sha(p):
    h=hashlib.sha256(); h.update(p.read_bytes()); return h.hexdigest()
manifest={"status":"PRE_FREEZE_ONLY","files":[]}
for rel in TARGETS:
    p=ROOT/rel
    manifest["files"].append({"path":rel,"sha256":sha(p) if p.exists() else None})
out=ROOT/"freeze"/"pre_freeze_manifest.json"
out.write_text(json.dumps(manifest,indent=2),encoding="utf-8")
print(out)
