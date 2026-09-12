"""Deterministic policy/state engine for ARBM OSWorld v32."""
from dataclasses import dataclass, field
from enum import Enum
import re


class DecisionKind(str, Enum):
    EXEC = "EXEC"
    NOOP_VERIFIED = "NOOP_VERIFIED"
    HOLD_CAPACITY = "HOLD_CAPACITY"
    FINISH_CANDIDATE = "FINISH_CANDIDATE"


@dataclass
class WorldState:
    active_app: str = "unknown"
    current_source: str = ""
    source_read: bool = False
    foreground_visible: set[str] = field(default_factory=set)
    background_elements: set[str] = field(default_factory=set)
    verified_facts: set[str] = field(default_factory=set)
    completed_milestones: set[str] = field(default_factory=set)
    unmet_prerequisites: set[str] = field(default_factory=set)


def extract_state(active_app: str, observation: str, milestones=None) -> WorldState:
    obs = str(observation or "")
    state = WorldState(active_app=str(active_app or "unknown"))
    milestones = milestones or []
    archive = re.search(r"([\w .-]+\.zip)\b", obs, re.I)
    if "archive" in state.active_app.lower() and archive:
        state.current_source = re.sub(r"^(?:title|label|text|name)\s+", "", archive.group(1).strip(), flags=re.I)
    for name in re.findall(r"[\w .-]+\.(?:pdf|zip|pptx|docx|xlsx|png|jpg)\b", obs, re.I):
        if state.active_app.lower() in {"desktop", "files"}:
            state.foreground_visible.add(name.strip())
        else:
            state.background_elements.add(name.strip())
    for item in milestones:
        text = " ".join(str(item.get(k, "")) for k in ("name", "application", "visible_text", "verification")) if isinstance(item, dict) else str(item)
        state.completed_milestones.add(text.lower())
    if state.current_source:
        needle = state.current_source.lower()
        state.source_read = any(needle in m and any(w in m for w in ("read", "processed", "complete", "verified", "extracted")) for m in state.completed_milestones)
        if not state.source_read:
            state.unmet_prerequisites.add(f"read:{state.current_source}")
    return state


def classify_capacity(provider_available: bool) -> DecisionKind:
    return DecisionKind.EXEC if provider_available else DecisionKind.HOLD_CAPACITY


def enforce_policy(state: WorldState, proposed: dict) -> dict:
    kind = str(proposed.get("kind") or DecisionKind.EXEC.value)
    command = str(proposed.get("command") or "")
    checkpoint = proposed.get("checkpoint") or {}
    expected_app = str(checkpoint.get("application") or "").strip()

    if kind == DecisionKind.HOLD_CAPACITY.value:
        return {**proposed, "kind": kind, "command": ""}

    if kind == DecisionKind.FINISH_CANDIDATE.value and state.unmet_prerequisites:
        raise ValueError("FINISH_WITH_UNMET_PREREQUISITES")

    if kind == DecisionKind.NOOP_VERIFIED.value:
        visible = str(checkpoint.get("visible_text") or "").strip()
        if not visible or visible not in state.foreground_visible:
            raise ValueError("NOOP_REQUIRES_FOREGROUND_PROOF")
        return {**proposed, "command": ""}

    if kind != DecisionKind.EXEC.value:
        raise ValueError("INVALID_DECISION_KIND")

    if state.current_source and not state.source_read:
        lower = command.lower()
        switching = any(x in lower for x in ("hotkey('alt', 'tab')", "hotkey(\"alt\", \"tab\")", "hotkey('ctrl', 'win', 'd')", "hotkey('ctrl', 'super', 'd')"))
        if switching or (expected_app and expected_app.lower() not in state.active_app.lower()):
            raise ValueError("SOURCE_CONTEXT_LOCKED")
    return proposed


def decision_from_agent(action: dict, state: WorldState, provider_available=True) -> dict:
    """Translate legacy agent output into the v32 typed decision contract."""
    if not provider_available:
        return {"kind": DecisionKind.HOLD_CAPACITY.value, "command": "", "reason": "provider_capacity"}
    legacy = str(action.get("action") or "").lower()
    if legacy == "exec":
        proposal = {**action, "kind": DecisionKind.EXEC.value}
    elif legacy == "wait":
        proposal = {**action, "kind": DecisionKind.NOOP_VERIFIED.value}
    elif legacy == "finish":
        proposal = {**action, "kind": DecisionKind.FINISH_CANDIDATE.value}
    else:
        raise ValueError("INVALID_LEGACY_ACTION")
    return enforce_policy(state, proposal)


def apply_live_policy(action: dict, active_app: str, observation: str, milestones=None,
                      provider_available: bool = True) -> dict:
    """Apply v32 deterministic state extraction and policy to a live agent action."""
    state = extract_state(active_app, observation, milestones)
    return decision_from_agent(action, state, provider_available=provider_available)
