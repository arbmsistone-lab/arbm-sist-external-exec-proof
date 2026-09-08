"""Provider-neutral execution contract for ARBM SIST.

Critical execution must always expose three independent routes:
GitHub Actions, GitLab CI, and ARBM External Executor.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys
from typing import Mapping

PROVIDERS = ("github", "gitlab", "arbm-external")
TRUE_VALUES = {"1", "true", "yes", "on"}


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in TRUE_VALUES


@dataclass(frozen=True)
class ExecutorContext:
    provider: str
    workspace: str
    evidence_dir: str
    runner_name: str
    zero_spend_mode: str
    free_capacity_proven: bool

def detect_provider(env: Mapping[str, str]) -> str:
    matches = []
    if _truthy(env.get("GITHUB_ACTIONS")):
        matches.append("github")
    if _truthy(env.get("GITLAB_CI")):
        matches.append("gitlab")
    if _truthy(env.get("ARBM_EXTERNAL_EXEC")):
        matches.append("arbm-external")
    if len(matches) != 1:
        raise RuntimeError(f"EXECUTOR_PROVIDER_INVALID: matches={matches}")
    return matches[0]


def resolve_workspace(env: Mapping[str, str], cwd: Path | None = None) -> Path:
    raw = env.get("ARBM_WORKSPACE") or env.get("GITHUB_WORKSPACE") or env.get("CI_PROJECT_DIR")
    return Path(raw).resolve() if raw else (cwd or Path.cwd()).resolve()


def free_capacity_proven(provider: str, env: Mapping[str, str]) -> bool:
    if provider == "github":
        return env.get("RUNNER_ENVIRONMENT") == "github-hosted" and env.get("ARBM_REPO_VISIBILITY", "public") == "public"
    if provider == "gitlab":
        return _truthy(env.get("ARBM_GITLAB_FREE_RUNNER"))
    if provider == "arbm-external":
        return _truthy(env.get("ARBM_FREE_CAPACITY_PROVEN"))
    return False

def build_context(env: Mapping[str, str] | None = None) -> ExecutorContext:
    env = env or os.environ
    if env.get("ZERO_SPEND_MODE") != "HARD":
        raise RuntimeError("ZERO_SPEND_MODE_REQUIRED")
    provider = detect_provider(env)
    workspace = resolve_workspace(env)
    proven = free_capacity_proven(provider, env)
    if not proven:
        raise RuntimeError(f"FREE_CAPACITY_NOT_PROVEN:{provider}")
    evidence_dir = workspace / "p9-eval"
    runner = env.get("ARBM_RUNNER_NAME") or env.get("RUNNER_NAME") or env.get("CI_RUNNER_DESCRIPTION") or provider
    return ExecutorContext(provider, str(workspace), str(evidence_dir), runner, "HARD", True)


def main() -> int:
    try:
        ctx = build_context()
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(asdict(ctx), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
