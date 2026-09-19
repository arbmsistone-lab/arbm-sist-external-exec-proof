"""Replay v31 recorded observations through the v32 deterministic policy."""
from pathlib import Path
import json
import re

from osworld_v32_policy import apply_live_policy, extract_state
from replay_osworld_run30 import load_cases


def load_request(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("request", data)


def recorded_steps(root: Path):
    return sorted(root.rglob("shim-observations/step_*.json"))


def assert_background_never_foreground(req: dict):
    active = str(req.get("active_application") or "unknown")
    obs = str(req.get("observation") or "")
    state = extract_state(active, obs, req.get("verified_milestones", []))
    if active.lower() not in {"desktop", "files"}:
        assert not state.foreground_visible, (active, state.foreground_visible)
    return state


def main(run30: str, run38: str):
    report = {"run30_steps": 0, "run38_steps": 0, "checks": []}
    run30_tasks = {}
    for task, _d, traj, trees, _instruction in load_cases(Path(run30)):
        assert len(traj) == len(trees), (task, len(traj), len(trees))
        run30_tasks[task] = len(traj)
        for obs in trees:
            assert_background_never_foreground({"active_application":"unknown","observation":obs})
            report["run30_steps"] += 1
    assert run30_tasks == {"001":78,"002":70,"003":43}, run30_tasks
    assert report["run30_steps"] == 191, report["run30_steps"]
    report["checks"].append("run30_full_191_steps_replayed")

    r38 = Path(run38)
    for path in recorded_steps(r38):
        req = load_request(path)
        assert_background_never_foreground(req)
        report["run38_steps"] += 1

    task3 = next(r38.rglob("osworld-sovereign-003/shim-observations/step_0003.json"))
    req3 = load_request(task3)
    state3 = assert_background_never_foreground(req3)
    assert "archive" in state3.active_app.lower(), state3.active_app
    assert state3.current_source, "RECORDED_ARCHIVE_SOURCE_NOT_EXTRACTED"
    try:
        apply_live_policy({"action":"exec","command":"pyautogui.hotkey('ctrl', 'win', 'd')",
                           "checkpoint":{"application":"Desktop"}},
                          state3.active_app, str(req3.get("observation") or ""),
                          req3.get("verified_milestones", []))
    except ValueError as exc:
        assert str(exc) == "SOURCE_CONTEXT_LOCKED"
        report["checks"].append("recorded_archive_escape_blocked")
    else:
        raise AssertionError("RECORDED_ARCHIVE_ESCAPE_NOT_BLOCKED")

    report["checks"].append("recorded_background_never_foreground")
    print(json.dumps({"status":"V32_HISTORICAL_GATE_PASS", **report}, sort_keys=True))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("run30")
    p.add_argument("run38")
    a = p.parse_args()
    main(a.run30, a.run38)
