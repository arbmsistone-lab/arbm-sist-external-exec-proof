from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from .action_ir import ActionIR, ActionKind
from .legacy_bridge import world_from_legacy_observation

@dataclass(frozen=True)
class CompiledAction:
    legacy_action: Mapping[str, Any]
    action_digest: str

class LegacyExecutorAdapter:
    """Compile ActionIR through the existing OSWorld safety/grounding compiler.

    The adapter never invokes pyautogui directly. It emits a canonical legacy
    action that must pass osworld_control.canonical_action + ground_action.
    """
    def __init__(self, *, active_application: str,
                 observation_text: str="",
                 verified_milestones=None,
                 allow_canonical: bool=False,
                 verifier_result=None,
                 recent_commands=None):
        self.active_application=active_application
        self.observation_text=observation_text
        self.verified_milestones=list(verified_milestones or [])
        self.allow_canonical=bool(allow_canonical)
        self.verifier_result=verifier_result or {}
        self.recent_commands=list(recent_commands or [])

    def _legacy_target(self, action: ActionIR) -> dict:
        if action.target is None:
            return {}
        attrs=dict(action.target.attributes)
        target={
            "source":action.target.source,
            "entity_id":action.target.entity_id,
            "version":action.target.version,
        }
        for key in ("label","role","cx","cy","w","h","slide","proof_sha256",
                    "foreground_sha256","deck_sha256","shape_id","shape_name"):
            if key in attrs:
                target[key]=attrs[key]
        return target

    def _command(self, action: ActionIR) -> str:
        p=dict(action.payload)
        if action.kind == ActionKind.CLICK:
            if "x" not in p or "y" not in p:
                # Semantic targets are resolved by ground_action using the target.
                return "pyautogui.click(0, 0)"
            return f"pyautogui.click({int(p['x'])}, {int(p['y'])}, clicks={int(p.get('clicks',1))})"
        if action.kind == ActionKind.DOUBLE_CLICK:
            if "x" not in p or "y" not in p:
                return "pyautogui.doubleClick(0, 0)"
            return f"pyautogui.doubleClick({int(p['x'])}, {int(p['y'])})"
        if action.kind == ActionKind.TYPE_TEXT:
            text=str(p.get("text") or "")
            interval=float(p.get("interval",0.02))
            return f"pyautogui.write({text!r}, interval={interval!r})"
        if action.kind == ActionKind.HOTKEY:
            keys=tuple(str(x) for x in p.get("keys") or ())
            if not keys:
                raise ValueError("HOTKEY_KEYS_REQUIRED")
            return "pyautogui.hotkey("+", ".join(repr(x) for x in keys)+")"
        if action.kind == ActionKind.WAIT:
            return f"pyautogui.sleep({float(p.get('seconds',0))!r})"
        if action.kind == ActionKind.SAVE:
            return "pyautogui.hotkey('ctrl', 's')"
        if action.kind == ActionKind.FINISH:
            return ""
        if "legacy_command" in action.metadata:
            return str(action.metadata["legacy_command"])
        raise ValueError("ACTION_KIND_NOT_LEGACY_EXECUTABLE:"+action.kind.value)

    def compile(self, action: ActionIR) -> CompiledAction:
        from osworld_control import canonical_action, ground_action
        action.validate()
        if action.kind == ActionKind.FINISH:
            legacy={"action":"finish","command":"","target":self._legacy_target(action)}
        elif action.kind == ActionKind.WAIT:
            legacy={"action":"wait","command":"","target":self._legacy_target(action),
                    "plan":str(action.metadata.get("plan") or "bounded wait")}
        else:
            legacy={
                "action":"exec",
                "command":self._command(action),
                "target":self._legacy_target(action),
                "plan":str(action.metadata.get("plan") or action.metadata.get("objective") or action.kind.value),
            }
        canonical=canonical_action(legacy)
        grounded=ground_action(
            canonical,
            self.active_application,
            observation=self.observation_text,
            verified_milestones=self.verified_milestones,
            allow_canonical=self.allow_canonical,
            verifier_result=self.verifier_result,
            recent_commands=self.recent_commands,
        )
        return CompiledAction(grounded,action.digest)

    def executor(self, dispatch: Callable[[Mapping[str, Any]], Mapping[str, Any]]):
        def run(action: ActionIR) -> Mapping[str, Any]:
            compiled=self.compile(action)
            result=dict(dispatch(compiled.legacy_action) or {})
            result.setdefault("compiled_action",dict(compiled.legacy_action))
            result.setdefault("action_digest",compiled.action_digest)
            return result
        return run

class LegacyObservationAdapter:
    def __init__(self, observe_legacy: Callable[[], Mapping[str, Any]]):
        self.observe_legacy=observe_legacy

    def observe_world(self):
        return world_from_legacy_observation(self.observe_legacy())