#!/usr/bin/env python3
"""Final fail-closed certification board for Task 091.

This board is intentionally post-focal only. Pre-focal review boards may advise,
but cannot approve release. Final certification requires same-run/same-SHA
official evidence, exact score 1.0, visual 13/13, zero fatal shim events, and
exact final KPI table values on slide 3.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from arbm091.score_tracker import certify, read_text, scan_fatal
from arbm091.trace_gate import require

EXPECTED_SLIDE3_TABLE = {
    "Table 12#r1c2": "$40.9M",
    "Table 12#r2c2": "104%",
    "Table 12#r3c2": "71%",
    "Table 12#r4c2": "$2.8M",
    "Table 12#r5c2": "3",
    "Table 12#r6c2": "206",
}


def _latest_observation(root: Path) -> dict:
    candidates = sorted((root / "wps-observations").glob("*.json"))
    require(bool(candidates), "FINAL_WPS_OBSERVATION_MISSING")
    for path in reversed(candidates):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        shapes = row.get("deck_slide_shapes")
        if isinstance(shapes, dict) and isinstance(shapes.get("3"), list):
            return row
    raise ValueError("FINAL_WPS_OBSERVATION_WITH_SLIDE3_MISSING")


def _verify_slide3_table(root: Path) -> dict:
    obs = _latest_observation(root)
    rows = {}
    for shape in obs["deck_slide_shapes"]["3"]:
        if str(shape.get("kind") or "") != "table-cell":
            continue
        rows[str(shape.get("name") or "")] = str(shape.get("text") or "")
    mismatches = {
        name: {"expected": expected, "actual": rows.get(name)}
        for name, expected in EXPECTED_SLIDE3_TABLE.items()
        if rows.get(name) != expected
    }
    require(not mismatches, "FINAL_SLIDE3_TABLE_MISMATCH:" + json.dumps(mismatches, sort_keys=True))
    return {name: rows[name] for name in EXPECTED_SLIDE3_TABLE}


def _verify_visual(root: Path) -> dict:
    log = read_text(root, "osworld.log")
    matches = re.findall(r"TASK091_SECTION_E_SCORE=([0-9.]+)/0\.3000 VISUAL_GATES=(\d+)/13 E_PENALTY=([0-9.]+)", log)
    require(bool(matches), "FINAL_VISUAL_GATE_EVIDENCE_MISSING")
    score, passed, penalty = matches[-1]
    require(score == "0.3000", "SECTION_E_NOT_FULL_SCORE:" + score)
    require(passed == "13", "VISUAL_GATES_NOT_13_OF_13:" + passed)
    require(penalty in ("0", "0.0", "0.00", "0.000", "0.0000"), "SECTION_E_PENALTY_NONZERO:" + penalty)
    failures = re.findall(r"TASK091_SECTION_E_FAILURES=([^\n\r]*)", log)
    if failures:
        require(failures[-1].strip() in ("", "NONE", "none", "[]"), "SECTION_E_FAILURE_PRESENT:" + failures[-1].strip())
    return {"section_e_score": score, "visual_gates": "13/13", "penalty": penalty}


def certify_final(root: Path, sha: str, run_id: str, run_attempt: str, jobs: dict) -> dict:
    expected_jobs = ("proof-tests", "policy", "replay", "focal-091")
    for name in expected_jobs:
        require(jobs.get(name) == "success", "FINAL_JOB_NOT_SUCCESS:" + name + "=" + str(jobs.get(name)))
    require(read_text(root, "candidate-sha.txt") == sha, "FINAL_SHA_MISMATCH")
    require(read_text(root, "run-id.txt") == run_id, "FINAL_RUN_ID_MISMATCH")
    require(read_text(root, "run-attempt.txt") == run_attempt, "FINAL_RUN_ATTEMPT_MISMATCH")
    scan_fatal(root, final=True)
    focal = certify(root, sha, run_id, run_attempt)
    visual = _verify_visual(root)
    table = _verify_slide3_table(root)
    return {
        "status": "TASK091_FINAL_CERTIFICATION_PASS",
        "release_approval": True,
        "candidate_sha": sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "jobs": jobs,
        "official_score": focal["official"]["score"],
        "visual": visual,
        "slide3_table": table,
        "focal_status": focal["status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True)
    parser.add_argument("--jobs-json", required=True)
    args = parser.parse_args()
    try:
        jobs = json.loads(args.jobs_json)
        require(isinstance(jobs, dict), "FINAL_JOBS_SCHEMA_INVALID")
        verdict = certify_final(args.root, args.sha, args.run_id, args.run_attempt, jobs)
        print(json.dumps(verdict, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({
            "status": "TASK091_FINAL_CERTIFICATION_FAIL",
            "release_approval": False,
            "reason": str(exc),
            "type": type(exc).__name__,
        }, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
