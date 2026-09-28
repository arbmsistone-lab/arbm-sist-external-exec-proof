from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Any

class RootCause(str, Enum):
    OBSERVATION_STALE="observation_stale"
    TARGET_DRIFT="target_drift"
    SAVE_NOT_PERSISTED="save_not_persisted"
    GEOMETRY_MISMATCH="geometry_mismatch"
    APPLICATION_MODAL="application_modal"
    PROVIDER_FAILURE="provider_failure"
    POLICY_REJECTED="policy_rejected"
    NO_PROGRESS="no_progress"
    EXECUTION_REJECTED="execution_rejected"
    UNKNOWN="unknown"

@dataclass(frozen=True)
class RecoveryDecision:
    root_cause: RootCause
    action: str
    retryable: bool
    max_retries: int
    evidence: Mapping[str, Any]

class RootCauseClassifier:
    def classify(self, code: str, evidence: Mapping[str, Any] | None=None) -> RecoveryDecision:
        text=str(code or "").upper()
        ev=evidence or {}
        table=(
            (("STALE","OBSERV"),RootCause.OBSERVATION_STALE,"refresh_observation",True,1),
            (("DRIFT","VERSION"),RootCause.TARGET_DRIFT,"re_ground_target",True,1),
            (("SAVE","PERSIST"),RootCause.SAVE_NOT_PERSISTED,"verify_then_rollback",True,1),
            (("GEOMETRY","CONTAIN"),RootCause.GEOMETRY_MISMATCH,"recompute_geometry",True,1),
            (("MODAL",),RootCause.APPLICATION_MODAL,"dismiss_bounded_modal",True,1),
            (("PROVIDER","CAPACITY"),RootCause.PROVIDER_FAILURE,"route_alternate_free_provider",True,2),
            (("EXECUTION_REJECTED",),RootCause.EXECUTION_REJECTED,"reexecute_bounded",True,1),
            (("POLICY","SENIOR_ELITE","ANTI_REPETITION"),RootCause.POLICY_REJECTED,"halt_and_replan",False,0),
            (("NO_STATE_CHANGE","NO_PROGRESS"),RootCause.NO_PROGRESS,"reobserve_then_replan",True,1),
        )
        for needles,cause,action,retryable,max_retries in table:
            if any(n in text for n in needles):
                return RecoveryDecision(cause,action,retryable,max_retries,ev)
        return RecoveryDecision(RootCause.UNKNOWN,"halt_for_diagnosis",False,0,ev)