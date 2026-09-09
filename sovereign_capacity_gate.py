import io
import json
import os
import statistics
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

EVIDENCE = Path("evidence/SOVEREIGN-3M-CAPACITY-20260909.json")
TARGET = 3_000_000
MIN_TPS = TARGET / 86_400
API = "https://api.github.com/repos/arbmsistone-lab/arbm-sist-external-exec-proof"


def _request(path):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN_REQUIRED")
    req = urllib.request.Request(
        API + path,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read()


def _json(path):
    return json.loads(_request(path))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _artifact_zip(artifact_id):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN_REQUIRED")
    req = urllib.request.Request(
        API + f"/actions/artifacts/{artifact_id}/zip",
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=30) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        if exc.code not in (301, 302, 303, 307, 308):
            raise
        location = exc.headers.get("Location")
        if not location:
            raise RuntimeError("ARTIFACT_REDIRECT_MISSING_LOCATION")
        with urllib.request.urlopen(location, timeout=30) as response:
            return response.read()


def _artifact_json(run_id, artifact_name, member):
    listing = _json(f"/actions/runs/{run_id}/artifacts")
    matches = [a for a in listing.get("artifacts", []) if a.get("name") == artifact_name]
    if len(matches) != 1:
        raise RuntimeError(f"ARTIFACT_COUNT_{artifact_name}_{len(matches)}")
    raw = _artifact_zip(matches[0]["id"])
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        return json.loads(archive.read(member))


def _validate_static(data):
    shards = data.get("shards") or []
    rotations = data.get("rotation_generations") or []
    return (
        data.get("zero_spend_mode") == "HARD"
        and data.get("throughput_gate") == "PASS"
        and data.get("rotation_gate") == "PASS"
        and len(shards) == 4
        and sorted(s.get("id") for s in shards) == [1, 2, 3, 4]
        and float(data.get("aggregate_tokens_per_s", 0)) >= MIN_TPS
        and int(data.get("projected_daily_tokens", 0)) >= TARGET
        and rotations == [0, 1, 2]
        and len(data.get("rotation_runs") or []) == 3
    )

def _validate_remote(data):
    run_id = int(data["throughput_run"])
    run = _json(f"/actions/runs/{run_id}")
    if run.get("conclusion") != "success" or run.get("head_sha") != data.get("tested_sha"):
        raise RuntimeError("THROUGHPUT_RUN_NOT_IMMUTABLY_MATCHED")
    measured = []
    for shard_id in (1, 2, 3, 4):
        row = _artifact_json(run_id, f"sovereign-3m-shard-{shard_id}", "throughput.json")
        samples = row.get("samples") or []
        if row.get("shard") != shard_id or len(samples) < 3:
            raise RuntimeError(f"INVALID_SHARD_{shard_id}")
        rates = [float(s["tokens"]) / float(s["elapsed_s"]) for s in samples]
        measured.append(statistics.median(rates))
    total = sum(measured)
    if int(total * 86_400) < TARGET:
        raise RuntimeError("REMOTE_THROUGHPUT_BELOW_TARGET")
    rotation_runs = data.get("rotation_runs") or []
    for generation, rotation_run in enumerate(rotation_runs):
        run = _json(f"/actions/runs/{rotation_run}")
        if run.get("conclusion") != "success" or run.get("head_sha") != data.get("rotation_sha"):
            raise RuntimeError(f"ROTATION_RUN_INVALID_{generation}")
        row = _artifact_json(rotation_run, f"sovereign-capacity-rotation-{generation}", "rotation-evidence.json")
        if int(row.get("generation", -1)) != generation or str(row.get("run_id")) != str(rotation_run):
            raise RuntimeError(f"ROTATION_ARTIFACT_INVALID_{generation}")
    return round(total, 3), int(total * 86_400)


def certify_sovereign_capacity():
    try:
        data = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"certified": False, "status": "FAIL_MISSING_OR_INVALID_SOVEREIGN_EVIDENCE"}
    if not _validate_static(data):
        return {"certified": False, "status": "FAIL_INVALID_SOVEREIGN_EVIDENCE"}
    aggregate = float(data.get("aggregate_tokens_per_s", 0))
    daily = int(data.get("projected_daily_tokens", 0))
    if os.environ.get("REQUIRE_REMOTE_SOVEREIGN_EVIDENCE") == "1":
        try:
            aggregate, daily = _validate_remote(data)
        except Exception as exc:
            return {"certified": False, "status": "FAIL_REMOTE_SOVEREIGN_EVIDENCE", "error": str(exc)}
    return {
        "certified": True,
        "status": "PASS_QUANTITATIVE_SOVEREIGN_CAPACITY",
        "throughput_run": data.get("throughput_run"),
        "aggregate_tokens_per_s": aggregate,
        "projected_daily_tokens": daily,
        "target_daily_tokens": TARGET,
        "rotation_runs": data.get("rotation_runs"),
        "scope": data.get("claim_scope"),
    }
