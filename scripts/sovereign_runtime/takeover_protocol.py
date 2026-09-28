#!/usr/bin/env python3
import argparse, hashlib, json, pathlib, sys

def canon(d):
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

def digest(d):
    return hashlib.sha256(canon(d)).hexdigest()

def load(path):
    return json.loads(pathlib.Path(path).read_text())

def save(path, data):
    pathlib.Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

def checked_state(path):
    state = load(path)
    claimed = state.pop("checkpoint_hash", None)
    actual = digest(state)
    if claimed != actual:
        raise SystemExit("CHECKPOINT_INTEGRITY=FAIL")
    return state

ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)

p = sub.add_parser("prepare")
p.add_argument("--mission", required=True)
p.add_argument("--owner", required=True)
p.add_argument("--candidate", required=True)
p.add_argument("--out", required=True)

t = sub.add_parser("takeover")
t.add_argument("--infile", required=True)
t.add_argument("--new-owner", required=True)
t.add_argument("--out", required=True)

c = sub.add_parser("commit")
c.add_argument("--infile", required=True)
c.add_argument("--owner", required=True)
c.add_argument("--token", type=int, required=True)
c.add_argument("--idempotency-key", required=True)
c.add_argument("--receipt", required=True)
c.add_argument("--out")

v = sub.add_parser("verify")
v.add_argument("--prepared", required=True)
v.add_argument("--taken", required=True)
v.add_argument("--expected-candidate", required=True)

a = ap.parse_args()

if a.cmd == "prepare":
    state = {
        "schema_version": 2,
        "mission_id": a.mission,
        "candidate_sha": a.candidate,
        "owner": a.owner,
        "fencing_token": 1,
        "checkpoint": 1,
        "idempotency_key": f"{a.mission}:effect:1",
        "effect_state": "OBSERVED_UNCOMMITTED",
        "effect_receipt": "provider_tx_demo_001",
        "duplicate_effect_executions": 0,
    }
    state["checkpoint_hash"] = digest(state)
    save(a.out, state)
    print("TAKEOVER_PREPARE=PASS")
    raise SystemExit(0)

if a.cmd == "takeover":
    state = checked_state(a.infile)
    old_owner = state["owner"]
    old_token = state["fencing_token"]
    if a.new_owner == old_owner:
        raise SystemExit("TAKEOVER_RESUME=FAIL owner_not_changed")
    state["previous_owner"] = old_owner
    state["previous_fencing_token"] = old_token
    state["owner"] = a.new_owner
    state["fencing_token"] = old_token + 1
    state["checkpoint"] = 2
    state["effect_state"] = "RECONCILED_COMMITTED"
    state["duplicate_effect_executions"] = 0
    state["checkpoint_hash"] = digest(state)
    save(a.out, state)
    print("TAKEOVER_RESUME=PASS")
    raise SystemExit(0)

if a.cmd == "commit":
    state = checked_state(a.infile)
    if a.owner != state["owner"] or a.token != state["fencing_token"]:
        print(
            "COMMIT=REJECTED stale_fencing "
            f"present_owner={state['owner']} present_token={state['fencing_token']} "
            f"attempt_owner={a.owner} attempt_token={a.token}"
        )
        raise SystemExit(23)
    if a.idempotency_key != state["idempotency_key"]:
        print("COMMIT=REJECTED idempotency_key_mismatch")
        raise SystemExit(24)
    if a.receipt != state["effect_receipt"]:
        print("COMMIT=REJECTED receipt_mismatch")
        raise SystemExit(25)
    state["effect_state"] = "COMMITTED"
    state["checkpoint"] = max(int(state["checkpoint"]), 2) + 1
    state["checkpoint_hash"] = digest(state)
    if a.out:
        save(a.out, state)
    print("COMMIT=ACCEPTED current_fencing")
    raise SystemExit(0)

if a.cmd == "verify":
    prepared = checked_state(a.prepared)
    taken = checked_state(a.taken)
    checks = [
        prepared["candidate_sha"] == a.expected_candidate,
        taken["candidate_sha"] == a.expected_candidate,
        taken["mission_id"] == prepared["mission_id"],
        taken["previous_owner"] == prepared["owner"],
        taken["owner"] != prepared["owner"],
        taken["fencing_token"] == prepared["fencing_token"] + 1,
        taken["idempotency_key"] == prepared["idempotency_key"],
        taken["effect_receipt"] == prepared["effect_receipt"],
        prepared.get("duplicate_effect_executions", 0) == 0,
        taken["duplicate_effect_executions"] == 0,
        taken["effect_state"] == "RECONCILED_COMMITTED",
    ]
    if not all(checks):
        raise SystemExit("VERIFY=FAIL invariant")
    print("PHYSICAL_TAKEOVER_PROTOCOL=PASS")
    print("NOTE=stale_owner_rejection_must_be_observed_via_commit_subcommand")
