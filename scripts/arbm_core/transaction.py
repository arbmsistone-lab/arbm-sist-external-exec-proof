from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Mapping, Any
from .action_ir import ActionIR
from .recovery import RootCauseClassifier, RecoveryDecision
from .verifier import IndependentVerifier, VerificationResult
from .world_model import WorldModel

@dataclass(frozen=True)
class TransactionResult:
    committed: bool
    action_digest: str
    attempts: int
    pre: VerificationResult
    post: VerificationResult | None
    recovery: RecoveryDecision | None
    rollback_performed: bool
    evidence: Mapping[str, Any]
    recovered: bool = False

class TransactionCoordinator:
    def __init__(self, verifier: IndependentVerifier | None=None,
                 classifier: RootCauseClassifier | None=None):
        self.verifier=verifier or IndependentVerifier()
        self.classifier=classifier or RootCauseClassifier()

    def execute(self, action: ActionIR, before: WorldModel,
                executor: Callable[[ActionIR], Mapping[str, Any]],
                observe: Callable[[], WorldModel],
                rollback: Callable[[ActionIR, Mapping[str, Any]], None] | None=None) -> TransactionResult:
        pre=self.verifier.verify_pre(action,before)
        if not pre.passed:
            recovery=self.classifier.classify(pre.code,pre.evidence)
            return TransactionResult(False,action.digest,0,pre,None,recovery,False,{})
        last_post=None
        exec_evidence={}
        for attempt in range(1,action.max_attempts+1):
            exec_evidence=dict(executor(action) or {})
            if exec_evidence.get("accepted") is False:
                kind=str(exec_evidence.get("kind") or "").upper()
                code=("PROVIDER_FAILURE" if kind=="PROVIDER" else "EXECUTION_REJECTED")
                post=VerificationResult(False,code,exec_evidence)
            else:
                after=observe()
                post=self.verifier.verify_post(action,before,after)
            last_post=post
            if post.passed:
                return TransactionResult(True,action.digest,attempt,pre,post,None,False,exec_evidence,attempt>1)
            recovery=self.classifier.classify(post.code,post.evidence)
            if not recovery.retryable or attempt >= min(action.max_attempts,max(1,recovery.max_retries+1)):
                rolled=False
                if rollback is not None and action.rollback is not None:
                    rollback(action,exec_evidence)
                    rolled=True
                return TransactionResult(False,action.digest,attempt,pre,post,recovery,rolled,exec_evidence)
        recovery=self.classifier.classify(last_post.code if last_post else "UNKNOWN", last_post.evidence if last_post else {})
        return TransactionResult(False,action.digest,action.max_attempts,pre,last_post,recovery,False,exec_evidence)