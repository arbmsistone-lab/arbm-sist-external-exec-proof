from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
import hashlib
import json

class ActionKind(str, Enum):
    OBSERVE="observe"
    CLICK="click"
    DOUBLE_CLICK="double_click"
    TYPE_TEXT="type_text"
    HOTKEY="hotkey"
    WAIT="wait"
    SAVE="save"
    FILE_EDIT="file_edit"
    API_CALL="api_call"
    FINISH="finish"

@dataclass(frozen=True)
class TargetRef:
    entity_id: str
    source: str
    version: str
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.entity_id.strip():
            raise ValueError("TARGET_ENTITY_REQUIRED")
        if not self.source.strip():
            raise ValueError("TARGET_SOURCE_REQUIRED")
        if not self.version.strip():
            raise ValueError("TARGET_VERSION_REQUIRED")

@dataclass(frozen=True)
class ActionIR:
    kind: ActionKind
    target: TargetRef | None
    payload: Mapping[str, Any]
    preconditions: tuple[str, ...]
    postconditions: tuple[str, ...]
    rollback: Mapping[str, Any] | None = None
    max_attempts: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.kind not in (ActionKind.OBSERVE, ActionKind.WAIT, ActionKind.FINISH) and self.target is None:
            raise ValueError("ACTION_TARGET_REQUIRED")
        if self.target is not None:
            self.target.validate()
        if self.max_attempts < 1 or self.max_attempts > 3:
            raise ValueError("ACTION_ATTEMPTS_OUT_OF_RANGE")
        if self.kind == ActionKind.TYPE_TEXT and "text" not in self.payload:
            raise ValueError("TYPE_TEXT_PAYLOAD_REQUIRED")
        if self.kind == ActionKind.CLICK:
            clicks=int(self.payload.get("clicks",1))
            if clicks < 1 or clicks > 3:
                raise ValueError("CLICK_BOUND_VIOLATION")
        if self.kind == ActionKind.WAIT:
            seconds=float(self.payload.get("seconds",0))
            if seconds < 0 or seconds > 3:
                raise ValueError("WAIT_BOUND_VIOLATION")
        if self.kind not in (ActionKind.OBSERVE, ActionKind.WAIT) and not self.postconditions:
            raise ValueError("POSTCONDITION_REQUIRED")

    @property
    def digest(self) -> str:
        body={
            "kind":self.kind.value,
            "target":None if self.target is None else {
                "entity_id":self.target.entity_id,
                "source":self.target.source,
                "version":self.target.version,
                "attributes":dict(self.target.attributes),
            },
            "payload":dict(self.payload),
            "preconditions":list(self.preconditions),
            "postconditions":list(self.postconditions),
            "rollback":None if self.rollback is None else dict(self.rollback),
            "max_attempts":self.max_attempts,
            "metadata":dict(self.metadata),
        }
        return hashlib.sha256(json.dumps(body,sort_keys=True,default=str).encode()).hexdigest()