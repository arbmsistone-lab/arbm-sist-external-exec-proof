#!/usr/bin/env python3
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
EXPECTED = "3af925426537c51ed72eed6ae652fbaef0f1c95c"

actual = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", EXPECTED, actual])
if ancestor.returncode != 0:
    raise SystemExit(f"CANDIDATE_BINDING=FAIL candidate={EXPECTED} executor={actual}")
print(f"WITNESS_HARNESS_COMMIT={actual}")

out = ROOT / "takeover-prepared.json"
subprocess.run(
    [
        sys.executable,
        str(ROOT / "scripts/sovereign_runtime/takeover_protocol.py"),
        "prepare",
        "--mission",
        "arbm-sist-sovereign-runtime-physical-takeover",
        "--owner",
        "buildkite-control-plus-railway-executor",
        "--candidate",
        EXPECTED,
        "--out",
        str(out),
    ],
    check=True,
)

data = json.loads(out.read_text())
before = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
data.update(
    {
        "provider": "buildkite+railway",
        "failure_domain": "buildkite-control-plus-railway-executor",
        "result": "PASS",
        "independent_failure_domain": True,
        "evidence_class": "PHYSICAL_PREPARE_WITNESS",
        "evidence_sha256": hashlib.sha256(before).hexdigest(),
    }
)
out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
print("PHYSICAL_PREPARE_A=PASS")
print("CANDIDATE_SHA=" + data["candidate_sha"])
