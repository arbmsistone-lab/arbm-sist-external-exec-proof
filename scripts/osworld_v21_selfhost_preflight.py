#!/usr/bin/env python3
"""Preparation-only fail-closed preflight for OSWorld V2.1 self-hosted website.

This script does not start Docker, deploy services, alter DNS, or run OSWorld tasks.
It validates that a future remote host is correctly prepared and that the full
benchmark remains blocked unless separately authorized in the pins manifest.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


class PreflightError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise PreflightError(f"missing file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PreflightError(f"invalid JSON: {path}: {exc}") from exc


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
        raise PreflightError(f"git command failed: {' '.join(args)}") from exc
    return p.stdout.strip()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PreflightError(message)


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--pins",
        type=Path,
        default=Path("docs/international-recognition/osworld-v2.1-pins.json"),
    )
    parser.add_argument("--website-checkout", type=Path, default=Path("osworld-web"))
    parser.add_argument("--host-suffix", required=True)
    parser.add_argument("--scheme", choices=("http", "https"), default="http")
    parser.add_argument(
        "--allow-full-run",
        action="store_true",
        help="Fails unless the manifest also explicitly authorizes the full run.",
    )
    args = parser.parse_args()

    try:
        pins = load_json(args.pins.resolve())
        policy = pins["policy"]
        website = pins["website"]

        require(policy["zero_spend_mode"] == "HARD", "ZERO_SPEND_MODE must be HARD")
        require(policy["paid_fallback"] is False, "paid fallback must remain false")
        require(policy["heavy_local"] == 0, "heavy_local must remain 0")
        require(policy["fail_closed_provenance"] is True, "provenance must remain fail-closed")
        require(website["deployment_mode"] == "self_hosted", "website deployment_mode must be self_hosted")

        host_suffix = args.host_suffix.strip().lower().rstrip(".")
        require(bool(host_suffix), "host suffix is empty")
        require("/" not in host_suffix and "://" not in host_suffix, "host suffix must be a DNS suffix only")
        require(host_suffix not in {"localhost", "127.0.0.1"}, "remote verified preparation cannot use localhost")

        checkout = args.website_checkout.resolve()
        require(checkout.exists(), f"website checkout missing: {checkout}")
        require((checkout / ".git").exists(), "website checkout is not a git checkout")

        actual_head = git_output(checkout, "rev-parse", "HEAD")
        require(actual_head == website["commit"], f"website SHA mismatch: {actual_head} != {website['commit']}")

        status = git_output(checkout, "status", "--porcelain")
        require(status == "", "website checkout has uncommitted changes")

        require((checkout / "docker-compose.yml").exists(), "generated docker-compose.yml missing")
        require((checkout / ".gitmodules").exists(), ".gitmodules missing")

        require(command_exists("docker"), "docker command not available")
        try:
            subprocess.run(
                ["docker", "compose", "version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise PreflightError("docker compose plugin not available") from exc

        if args.allow_full_run:
            require(policy["full_run_authorized"] is True, "full benchmark remains blocked by manifest")
        else:
            require(policy["full_run_authorized"] is False, "unexpected manifest state: full run already authorized")

        result = {
            "status": "PASS",
            "mode": "PREPARATION_ONLY",
            "website_commit": actual_head,
            "host_suffix": host_suffix,
            "scheme": args.scheme,
            "docker_available": True,
            "docker_compose_available": True,
            "zero_spend_mode": policy["zero_spend_mode"],
            "paid_fallback": policy["paid_fallback"],
            "heavy_local": policy["heavy_local"],
            "full_run_authorized": policy["full_run_authorized"],
            "containers_started": False,
            "benchmark_started": False,
        }
        print(json.dumps(result, sort_keys=True))
        return 0
    except (KeyError, PreflightError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    sys.exit(main())
