from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping
from .action_ir import ActionIR
from .world_model import WorldModel

@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    code: str
    evidence: Mapping[str, Any]

class IndependentVerifier:
    def verify_pre(self, action: ActionIR, world: WorldModel) -> VerificationResult:
        action.validate()
        if world.conflicts:
            return VerificationResult(False,"WORLD_MODEL_CONFLICT",{"conflicts":world.conflicts})
        if action.target is not None:
            try:
                entity=world.require_entity(action.target.entity_id)
            except Exception as exc:
                return VerificationResult(False,"TARGET_NOT_GROUNDED",{"error":str(exc)})
            if entity.version != action.target.version:
                return VerificationResult(False,"TARGET_VERSION_DRIFT",{"expected":action.target.version,"actual":entity.version})
        return VerificationResult(True,"PRECONDITION_PASS",{"world_revision":world.revision})

    def verify_post(self, action: ActionIR, before: WorldModel, after: WorldModel) -> VerificationResult:
        if after.conflicts:
            return VerificationResult(False,"POST_WORLD_CONFLICT",{"conflicts":after.conflicts})
        if action.target is None:
            return VerificationResult(True,"POSTCONDITION_PASS",{"world_revision":after.revision})
        try:
            entity=after.require_entity(action.target.entity_id)
        except Exception as exc:
            return VerificationResult(False,"POST_TARGET_MISSING",{"error":str(exc)})
        field=action.payload.get("field")
        if field is not None and "value" in action.payload:
            actual=entity.attributes.get(str(field))
            expected=action.payload["value"]
            if actual != expected:
                return VerificationResult(False,"POSTCONDITION_MISMATCH",{"field":field,"expected":expected,"actual":actual})
        if before.revision == after.revision and action.kind.value not in ("observe","wait","finish"):
            return VerificationResult(False,"NO_STATE_CHANGE",{"revision":after.revision})
        return VerificationResult(True,"POSTCONDITION_PASS",{"world_revision":after.revision})