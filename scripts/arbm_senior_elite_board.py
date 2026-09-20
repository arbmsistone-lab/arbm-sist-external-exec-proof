"""ARBM SIST Senior Elite action admission board.

Ten independent deterministic review lanes. Every critical execution action must
pass unanimously before it may reach OSWorld. Pure logic: no network or guest
mutation.
"""
from __future__ import annotations
import ast
import os
import re

LANES = (
    "integrity",
    "security",
    "provenance",
    "specialist_ownership",
    "bounded_execution",
    "target_grounding",
    "anti_repetition",
    "progress_discipline",
    "zero_spend",
    "evidence_contract",
)

def _gui_calls(command):
    try:
        tree=ast.parse(str(command or ""))
    except SyntaxError:
        return []
    calls=[]
    for node in tree.body:
        if not isinstance(node,ast.Expr) or not isinstance(node.value,ast.Call):
            return []
        call=node.value
        if not (isinstance(call.func,ast.Attribute)
                and isinstance(call.func.value,ast.Name)
                and call.func.value.id=="pyautogui"):
            return []
        calls.append(call)
    return calls

def _lane(name, passed, reason):
    return {"lane":name,"pass":bool(passed),"reason":str(reason)}

def review_action(action, *, task_id="", source="generic", state=None,
                  verifier=None, recent_commands=None, zero_spend_mode=None,
                  github_sha=None):
    state=state if isinstance(state,dict) else {}
    verifier=verifier if isinstance(verifier,dict) else {}
    recent=[str(x or "") for x in (recent_commands or [])]
    a=action if isinstance(action,dict) else {}
    kind=str(a.get("action") or "")
    command=str(a.get("command") or "")
    target=a.get("target") if isinstance(a.get("target"),dict) else {}
    calls=_gui_calls(command) if kind=="exec" else []
    task091=state.get("task091_specialist") if isinstance(state.get("task091_specialist"),dict) else {}
    zero=str(zero_spend_mode if zero_spend_mode is not None else os.environ.get("ZERO_SPEND_MODE",""))
    sha=str(github_sha if github_sha is not None else os.environ.get("GITHUB_SHA",""))

    rows=[]
    rows.append(_lane("integrity",
        kind in {"exec","wait","finish"} and (kind!="exec" or bool(calls)),
        "typed action and parseable direct GUI calls required"))

    forbidden=(re.search(r"(?:/home/oai/share|powershell|cmd\.exe|subprocess|os\.system)",command,re.I)
               or ("hotkey" in command and "ctrl" in command and "alt" in command and "'t'" in command))
    rows.append(_lane("security",not bool(forbidden),
        "host paths, shells and terminal launch shortcuts are forbidden"))

    provenance_ok=(not sha) or bool(re.fullmatch(r"[0-9a-f]{40}",sha,re.I))
    rows.append(_lane("provenance",provenance_ok,
        "critical execution must be bound to an exact 40-hex commit when SHA is present"))

    ownership_ok=True
    if (str(task_id)=="091"
            and bool(task091.get("owned"))
            and not bool(task091.get("handoff"))
            and source!="task091-specialist"):
        ownership_ok=False
    rows.append(_lane("specialist_ownership",ownership_ok,
        "Task 091 specialist ownership cannot be bypassed by the generic mesh"))

    bounded_ok=(kind!="exec" or (1 <= len(calls) <= 8))
    if bounded_ok and kind=="exec":
        for call in calls:
            kwargs={kw.arg:ast.literal_eval(kw.value) for kw in call.keywords}
            if kwargs.get("presses",1)>30 or kwargs.get("clicks",1)>3 or kwargs.get("duration",0)>3:
                bounded_ok=False
                break
    rows.append(_lane("bounded_execution",bounded_ok,
        "actions are atomic/bounded and cannot contain unbounded GUI bursts"))

    pointer=kind=="exec" and bool(re.search(r"pyautogui\.(?:click|doubleClick|rightClick|dragTo)\s*\(",command))
    target_ok=(not pointer) or bool(str(target.get("source") or "").strip())
    rows.append(_lane("target_grounding",target_ok,
        "pointer actions require an explicit grounded target source"))

    repeated=bool(command and recent and command==recent[-1])
    no_progress=int(verifier.get("no_progress") or 0)
    phase=str(a.get("specialist_phase") or "")
    task091_state=state.get("task091_specialist") if isinstance(state.get("task091_specialist"),dict) else {}
    bounded_observation_retry=(
        str(task_id)=="091"
        and source=="task091-specialist"
        and command=="pyautogui.sleep(0.2)"
        and phase=="deck-a11y-resync"
        and no_progress==1
        and int(task091_state.get("deck_observation_retries") or 0)==1
    )
    anti_repeat=not (repeated and no_progress>0 and not bounded_observation_retry)
    rows.append(_lane("anti_repetition",anti_repeat,
        "no-progress actions cannot repeat except the single Task 091 deck observation resync explicitly bounded by specialist state"))

    progress_ok=not (
        kind=="finish"
        and (int(verifier.get("no_progress") or 0)>0 or verifier.get("progress") is False)
    )
    rows.append(_lane("progress_discipline",progress_ok,
        "finish is forbidden while current evidence reports no progress"))

    rows.append(_lane("zero_spend",zero=="HARD",
        "ARBM SIST execution requires ZERO_SPEND_MODE=HARD"))

    evidence_ok=not (
        kind=="exec"
        and source=="task091-specialist"
        and str(task_id)=="091"
        and not isinstance(state.get("task091_specialist"),dict)
    )
    rows.append(_lane("evidence_contract",evidence_ok,
        "critical specialist actions must execute inside a tracked specialist state"))

    failed=[row for row in rows if not row["pass"]]
    return {
        "allow":not failed,
        "pass":len(rows)-len(failed),
        "total":len(rows),
        "unanimous":not failed,
        "lanes":rows,
        "failed":[row["lane"] for row in failed],
    }

def require_unanimous(*args,**kwargs):
    result=review_action(*args,**kwargs)
    if not result["allow"]:
        raise ValueError("SENIOR_ELITE_VETO:"+",".join(result["failed"]))
    return result
