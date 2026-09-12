"""Offline v32 regression gate built from proven v31 failures."""
import json
from osworld_v32_policy import extract_state, decision_from_agent

CASES = [
    {
        "name": "background_tree_not_visible",
        "active_app": "Google Chrome",
        "observation": "label\tdegree_audit_report.pdf\nlabel\tSyllabus-CS-4Y.pdf",
        "agent": {"action":"wait","checkpoint":{"visible_text":"degree_audit_report.pdf"}},
        "expect_error": "NOOP_REQUIRES_FOREGROUND_PROOF",
    },
    {
        "name": "archive_context_lock",
        "active_app": "Archive Manager",
        "observation": "title filter.zip\nlabel city.zip",
        "agent": {"action":"exec","command":"pyautogui.hotkey('ctrl', 'win', 'd')","checkpoint":{"application":"Desktop"}},
        "expect_error": "SOURCE_CONTEXT_LOCKED",
    },
]

def main():
    results=[]
    for case in CASES:
        state=extract_state(case["active_app"],case["observation"])
        try:
            decision_from_agent(case["agent"],state)
            results.append({"case":case["name"],"pass":False,"reason":"unexpected_accept"})
        except ValueError as exc:
            ok=case["expect_error"] in str(exc)
            results.append({"case":case["name"],"pass":ok,"reason":str(exc)})
    if not all(x["pass"] for x in results):
        raise SystemExit(json.dumps(results))
    print(json.dumps({"status":"V32_REGRESSION_GATE_PASS","results":results}))


if __name__=="__main__":
    main()
