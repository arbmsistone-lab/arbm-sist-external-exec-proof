"""Fail-closed admission for the isolated G3 paid lane; never calls a model."""

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPOSITORY = "arbmsistone-lab/arbm-sist-external-exec-proof"
BRANCH = "g3/paid-cert-lane-20260910"
TOTAL_CAP = Decimal("10.00")


class PaidGateError(RuntimeError):
    pass


def money(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise PaidGateError("G3_BUDGET_INVALID") from None
    if not result.is_finite() or result < 0:
        raise PaidGateError("G3_BUDGET_INVALID")
    return result


def error_class(error):
    """Classify without persisting provider messages, credentials, or payloads."""
    message = str(error).lower()
    if "prepayment credits are depleted" in message or "insufficient credit" in message:
        return "PROVIDER_CREDIT_DEPLETED"
    code = getattr(error, "code", None)
    if code in (401, 403):
        return "PROVIDER_AUTH_DENIED"
    if code == 429:
        return "PROVIDER_QUOTA_EXHAUSTED"
    return "PROVIDER_REQUEST_UNRESOLVED"


def gui_action_violation(action):
    """Reject terminal launch/command text observed in earlier GUI trajectories.

    This is a defensive action filter, not proof that arbitrary GUI actions are
    semantically safe. A successful trajectory still requires an integrity audit.
    """
    name = str(action.get('action_type', '')).rsplit(':', 1)[-1].lower()
    params = action.get('parameters', {})
    if not isinstance(params, dict):
        return 'ACTION_PARAMETERS_INVALID'
    if name == 'hotkey':
        aliases = {'control_l': 'ctrl', 'control_r': 'ctrl', 'ctrlleft': 'ctrl',
                   'alt_l': 'alt', 'alt_r': 'alt', 'altleft': 'alt',
                   'super_l': 'win', 'winleft': 'win'}
        keys = {aliases.get(str(k).lower(), str(k).lower()) for k in params.get('keys', [])}
        if {'ctrl', 'alt', 't'} <= keys or {'win', 'r'} <= keys:
            return 'TERMINAL_LAUNCH_FORBIDDEN'
        if {'ctrl', 'alt'} <= keys and any(re.fullmatch(r'f\d+', k) for k in keys):
            return 'TERMINAL_LAUNCH_FORBIDDEN'
    if name == 'type':
        text = str(params.get('text', ''))
        if re.search(r'(?im)^\s*(?:sudo\s+)?(?:python[\d.]*|pip[\d.]*|apt(?:-get)?|'
                     r'bash|sh|zsh|powershell|pwsh|cmd(?:\.exe)?|node|npm|npx|'
                     r'curl|wget|chmod|cd|cat|source|eval|exec)\s+', text):
            return 'SHELL_COMMAND_OR_INSTALL_FORBIDDEN'
    if name == 'wait':
        seconds = params.get('seconds', 1)
        if not isinstance(seconds, (int, float)) or not math.isfinite(seconds) or not 0 <= seconds <= 2:
            return 'WAIT_EXCEEDS_TWO_SECONDS'
    return None


def admit(ledger, *, repository, branch, attempt, run_id, candidate_sha, history, root):
    if repository != REPOSITORY or branch != BRANCH:
        raise PaidGateError("G3_PAID_LANE_ISOLATION_REQUIRED")
    if str(attempt) != "1":
        raise PaidGateError("G3_RECONCILE_BEFORE_RERUN")
    if money(ledger.get("authorized_total_usd")) != TOTAL_CAP:
        raise PaidGateError("G3_AUTHORIZATION_MISMATCH")
    if ledger.get("reconciliation_status") != "COMPLETE":
        raise PaidGateError("G3_HISTORICAL_COST_UNRECONCILED")
    if ledger.get("provider_credit_status") != "AVAILABLE":
        raise PaidGateError("G3_PROVIDER_CREDIT_NOT_PROVEN")
    if ledger.get("per_call_cost_bound_status") != "PROVEN":
        raise PaidGateError("G3_PER_CALL_COST_BOUND_NOT_PROVEN")
    if not candidate_sha:
        raise PaidGateError("G3_CANDIDATE_SHA_REQUIRED")
    # A reservation can be consumed only once. Shared workflow concurrency plus
    # live history prevents two jobs from spending the same static allocation.
    accounted = {str(value) for value in ledger.get("accounted_run_ids", [])}
    if not history or len(history) >= 1000:
        raise PaidGateError("G3_RUN_HISTORY_INCOMPLETE")
    current = [r for r in history if str(r["databaseId"]) == str(run_id)]
    if len(current) != 1 or current[0]["headSha"] != candidate_sha:
        raise PaidGateError("G3_CURRENT_RUN_NOT_BOUND")
    for run in history:
        if "paid" not in run["workflowName"].lower() or str(run["databaseId"]) == str(run_id):
            continue
        if str(run["databaseId"]) not in accounted or run["status"] != "completed":
            raise PaidGateError("G3_UNACCOUNTED_OR_ACTIVE_PAID_RUN")
        if run["headSha"] == candidate_sha:
            raise PaidGateError("G3_RESERVATION_ALREADY_USED")
    spent = money(ledger.get("reconciled_total_usd"))
    reserve = money(ledger.get("reserved_run_usd"))
    if reserve <= 0 or spent + reserve > TOTAL_CAP:
        raise PaidGateError("G3_TOTAL_COST_CAP_REACHED")
    audits = ledger.get("audit_3x", {})
    if any(audits.get(key) != "PASS" for key in ("A", "B", "C")):
        raise PaidGateError("G3_AUDIT_3X_REQUIRED")
    hashes = ledger.get("audited_files_sha256", {})
    required = {
        "certification/g3_paid_control.py",
        "certification/g3-gemini-fc-adapter.py",
        ".github/workflows/osworld-g3-paid-smoke-v2.yml",
        ".github/workflows/osworld-g3-paid-model-probe.yml",
    }
    if not required.issubset(hashes):
        raise PaidGateError("G3_AUDIT_HASHES_REQUIRED")
    for name, digest in hashes.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not path.is_file():
            raise PaidGateError("G3_AUDIT_PATH_INVALID")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise PaidGateError("G3_AUDIT_HASH_MISMATCH")
    return {"state": "ADMITTED", "reserved_run_usd": str(reserve)}


def official_result(path):
    """Validate the official output; this never reads evaluator implementation."""
    try:
        value = float(Path(path).read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        raise PaidGateError("G3_OFFICIAL_RESULT_MISSING_OR_INVALID") from None
    if not math.isfinite(value) or value != 1.0:
        raise PaidGateError("G3_OFFICIAL_FULL_PASS_NOT_PROVEN")
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
        if ledger.get("reconciliation_status") != "COMPLETE":
            raise PaidGateError("G3_HISTORICAL_COST_UNRECONCILED")
        history = json.loads(subprocess.check_output([
            "gh", "run", "list", "--repo", REPOSITORY, "--branch", BRANCH,
            "--limit", "1000", "--json", "databaseId,headSha,status,workflowName",
        ], text=True, stderr=subprocess.DEVNULL))
        result = admit(
            ledger, repository=os.environ.get("GITHUB_REPOSITORY"),
            branch=os.environ.get("GITHUB_REF_NAME"),
            attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
            run_id=os.environ.get("GITHUB_RUN_ID"),
            candidate_sha=os.environ.get("GITHUB_SHA"), history=history, root=Path.cwd(),
        )
    except (PaidGateError, OSError, ValueError, subprocess.SubprocessError, KeyError) as error:
        code = str(error) if isinstance(error, PaidGateError) else "G3_LEDGER_INVALID"
        result = {"state": "BLOCKED", "reason": code, "paid_calls_started": 0}
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result))
    return 0 if result["state"] == "ADMITTED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
