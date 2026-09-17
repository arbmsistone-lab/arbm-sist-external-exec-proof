#!/usr/bin/env python3
"""Fail-closed verifier for ARBM SIST OSWorld V2.1 release pins.

This script is preparation-only until an explicitly authorized remote validation
lane executes it. It uses only Python's standard library and git.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


class VerificationError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VerificationError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise VerificationError(f"invalid JSON: {path}: {exc}") from exc


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    except FileNotFoundError as exc:
        raise VerificationError(f"missing file: {path}") from exc
    return h.hexdigest()


def git_output(checkout: Path, *args: str) -> str:
    try:
        p = subprocess.run(
            ["git", "-C", str(checkout), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise VerificationError(f"git command failed: {' '.join(args)}") from exc
    return p.stdout.strip()


def expect(actual: Any, expected: Any, field: str) -> None:
    if actual != expected:
        raise VerificationError(
            f"pin mismatch for {field}: actual={actual!r} expected={expected!r}"
        )


def nested(obj: dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            raise VerificationError(f"missing release field: {'.'.join(keys)}")
        cur = cur[key]
    return cur


def verify(checkout: Path, pins_path: Path, require_host_suffix: bool) -> dict[str, Any]:
    pins = load_json(pins_path)

    if nested(pins, "policy", "zero_spend_mode") != "HARD":
        raise VerificationError("ZERO_SPEND_MODE pin is not HARD")
    if nested(pins, "policy", "paid_fallback") is not False:
        raise VerificationError("paid fallback must remain false")
    if nested(pins, "policy", "heavy_local") != 0:
        raise VerificationError("heavy_local must remain 0")
    if nested(pins, "policy", "fail_closed_provenance") is not True:
        raise VerificationError("fail_closed_provenance must remain true")
    if nested(pins, "policy", "official_evaluator_integrity_required") is not True:
        raise VerificationError("official evaluator integrity must remain required")

    expected_head = nested(pins, "upstream", "tag_commit")
    actual_head = git_output(checkout, "rev-parse", "HEAD")
    expect(actual_head, expected_head, "upstream.tag_commit")

    manifest_path = checkout / nested(pins, "upstream", "manifest_path")
    release = load_json(manifest_path)

    expect(nested(release, "release"), nested(pins, "upstream", "tag"), "release")
    expect(nested(release, "status"), "active", "status")
    expect(
        nested(release, "osworld_code", "base_commit"),
        nested(pins, "upstream", "code_base_commit"),
        "osworld_code.base_commit",
    )
    expect(
        nested(release, "website_code", "commit"),
        nested(pins, "website", "commit"),
        "website_code.commit",
    )
    expect(
        nested(release, "tasks", "commit"),
        nested(pins, "tasks", "commit"),
        "tasks.commit",
    )
    expect(
        nested(release, "assets", "commit"),
        nested(pins, "assets", "commit"),
        "assets.commit",
    )
    expect(
        nested(release, "public_assets", "commit"),
        nested(pins, "public_assets", "commit"),
        "public_assets.commit",
    )
    expect(
        nested(release, "task_hash_manifest", "task_count"),
        nested(pins, "tasks", "task_count"),
        "task_hash_manifest.task_count",
    )
    expect(
        nested(release, "task_hash_manifest", "sha256").removeprefix("sha256:"),
        nested(pins, "tasks", "hash_manifest_sha256"),
        "task_hash_manifest.sha256",
    )
    expect(
        nested(release, "provider_images", "aws", "ubuntu", "us-east-1", "1920x1080", "ami_id"),
        nested(pins, "provider_images", "aws", "ami_id"),
        "provider_images.aws.ami_id",
    )
    expect(
        nested(release, "provider_images", "docker", "ubuntu", "artifact_revision"),
        nested(pins, "provider_images", "docker", "artifact_revision"),
        "provider_images.docker.artifact_revision",
    )
    expect(
        nested(release, "provider_images", "docker", "ubuntu", "artifact_sha256").removeprefix("sha256:"),
        nested(pins, "provider_images", "docker", "artifact_sha256"),
        "provider_images.docker.artifact_sha256",
    )
    expect(
        nested(release, "provider_images", "docker", "ubuntu", "runtime_image"),
        "happysixd/osworld-docker@" + nested(pins, "provider_images", "docker", "runtime_image_digest"),
        "provider_images.docker.runtime_image",
    )

    task_hash_manifest = checkout / nested(pins, "tasks", "hash_manifest_path")
    actual_task_manifest_sha = sha256_file(task_hash_manifest)
    expect(
        actual_task_manifest_sha,
        nested(pins, "tasks", "hash_manifest_sha256"),
        "local task hash manifest SHA256",
    )

    if require_host_suffix:
        host_suffix = nested(pins, "website", "host_suffix")
        if not isinstance(host_suffix, str) or not host_suffix.strip():
            raise VerificationError("website.host_suffix is not configured")

    return {
        "status": "PASS",
        "upstream_head": actual_head,
        "release": nested(release, "release"),
        "task_count": nested(release, "task_hash_manifest", "task_count"),
        "task_hash_manifest_sha256": actual_task_manifest_sha,
        "zero_spend_mode": nested(pins, "policy", "zero_spend_mode"),
        "paid_fallback": nested(pins, "policy", "paid_fallback"),
        "heavy_local": nested(pins, "policy", "heavy_local"),
        "full_run_authorized": nested(pins, "policy", "full_run_authorized"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkout", type=Path, default=Path("osworld"))
    parser.add_argument(
        "--pins",
        type=Path,
        default=Path("docs/international-recognition/osworld-v2.1-pins.json"),
    )
    parser.add_argument("--require-host-suffix", action="store_true")
    args = parser.parse_args()

    try:
        result = verify(args.checkout.resolve(), args.pins.resolve(), args.require_host_suffix)
    except VerificationError as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, sort_keys=True))
        return 1

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
