from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from .action_ir import ActionIR, ActionKind

@dataclass(frozen=True)
class AssuranceDecision:
    passed: bool
    reasons: tuple[str, ...]
    lanes: tuple[Mapping[str, Any], ...]

class AssurancePlane:
    def __init__(self, reviewer=None):
        self._reviewer=reviewer

    @staticmethod
    def _to_legacy_action(action: ActionIR) -> dict:
        target=None
        if action.target is not None:
            target={"source":action.target.source,"entity_id":action.target.entity_id,"version":action.target.version}
        command=str(action.metadata.get("legacy_command") or "")
        if action.kind == ActionKind.WAIT and not command:
            command=f"pyautogui.sleep({float(action.payload.get('seconds',0))})"
        return {"action":"exec" if action.kind not in (ActionKind.WAIT,ActionKind.FINISH) else action.kind.value,
                "command":command,"target":target or {}}

    def review(self, action: ActionIR, *, task_id="", source="vnext", state=None,
               verifier=None, recent_commands=None, zero_spend_mode="HARD", github_sha="") -> AssuranceDecision:
        action.validate()
        if self._reviewer is None:
            from arbm_senior_elite_board import review_action
            reviewer=review_action
        else:
            reviewer=self._reviewer
        legacy=self._to_legacy_action(action)
        result=reviewer(
            legacy,task_id=task_id,source=source,state=state or {},
            verifier=verifier or {},recent_commands=recent_commands or [],
            zero_spend_mode=zero_spend_mode,github_sha=github_sha,
        )
        lanes=tuple(result.get("lanes") or result.get("rows") or ())
        # Legacy Senior Elite returns an integer count in "pass" and a boolean
        # admission decision in "allow"/"unanimous". Never coerce the count.
        if "allow" in result:
            passed=bool(result["allow"])
        elif "unanimous" in result:
            passed=bool(result["unanimous"])
        elif "approved" in result:
            passed=bool(result["approved"])
        else:
            passed=bool(lanes) and all(bool(row.get("pass")) for row in lanes)
        reasons=tuple(
            str(row.get("lane") or row.get("reason") or "unknown")
            for row in lanes if not row.get("pass",False)
        )
        return AssuranceDecision(passed,reasons,lanes)