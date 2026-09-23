from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Any
from .assurance import AssurancePlane
from .planner import HierarchicalPlanner, Mission, Plan
from .transaction import TransactionCoordinator, TransactionResult
from .world_model import Evidence, WorldModel, fuse_world_state

@dataclass(frozen=True)
class RuntimeResult:
    mission_id: str
    planned: int
    committed: int
    success: bool
    world_revision: str
    transactions: tuple[TransactionResult, ...]
    failure: str = ""

class ARBMRuntime:
    def __init__(self, planner=None, assurance=None, transactions=None):
        self.planner=planner or HierarchicalPlanner()
        self.assurance=assurance or AssurancePlane()
        self.transactions=transactions or TransactionCoordinator()

    def run(self, mission: Mission, evidence: Iterable[Evidence],
            executor: Callable[[Any], Mapping[str, Any]],
            observe: Callable[[], WorldModel],
            rollback: Callable[[Any, Mapping[str, Any]], None] | None=None,
            *, task_id="", source="vnext", state=None, verifier_state=None,
            recent_commands=None, zero_spend_mode="HARD", github_sha="") -> RuntimeResult:
        world=fuse_world_state(evidence)
        if world.conflicts:
            return RuntimeResult(mission.mission_id,0,0,False,world.revision,(), "WORLD_MODEL_CONFLICT")
        plan=self.planner.plan(mission,world)
        txs=[]
        current=world
        for action in plan.actions:
            decision=self.assurance.review(
                action,task_id=task_id,source=source,state=state or {},
                verifier=verifier_state or {},recent_commands=recent_commands or [],
                zero_spend_mode=zero_spend_mode,github_sha=github_sha,
            )
            if not decision.passed:
                return RuntimeResult(mission.mission_id,len(plan.actions),len(txs),False,current.revision,tuple(txs),
                                     "ASSURANCE_REJECTED:"+",".join(decision.reasons))
            tx=self.transactions.execute(action,current,executor,observe,rollback)
            txs.append(tx)
            if not tx.committed:
                return RuntimeResult(mission.mission_id,len(plan.actions),sum(1 for x in txs if x.committed),
                                     False,current.revision,tuple(txs),
                                     tx.recovery.root_cause.value if tx.recovery else "TRANSACTION_FAILED")
            current=observe()
        return RuntimeResult(mission.mission_id,len(plan.actions),len(txs),True,current.revision,tuple(txs))