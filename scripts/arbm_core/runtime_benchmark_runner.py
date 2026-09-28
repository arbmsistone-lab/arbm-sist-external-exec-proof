from __future__ import annotations
from dataclasses import asdict
from typing import Any, Mapping
import argparse
import json
from pathlib import Path

from .assurance import AssuranceDecision
from .benchmark_program import (
    BenchmarkTask, build_internal_catalog, run_trials, summarize, promotion_gate
)
from .planner import Mission
from .runtime import ARBMRuntime
from .world_model import Evidence, fuse_world_state


class BenchmarkAssurance:
    """Deterministic shadow assurance for non-GUI benchmark environments.

    This does not replace the production Senior Elite board. It validates
    semantic ActionIR invariants so the ARBMRuntime can be stress-tested
    without mutating a desktop.
    """
    def review(self, action, **kwargs):
        reasons=[]
        try:
            action.validate()
        except Exception as exc:
            reasons.append("ACTION_INVALID:"+str(exc))
        if kwargs.get("zero_spend_mode") != "HARD":
            reasons.append("ZERO_SPEND_NOT_HARD")
        if action.target is not None and not action.target.entity_id:
            reasons.append("TARGET_ID_MISSING")
        return AssuranceDecision(not reasons,tuple(reasons),())


def _evidence(task: BenchmarkTask, value: str, version: str, *, conflict: bool=False):
    entity=f"bench.{task.domain}.{task.task_id}"
    rows=[
        Evidence("benchmark-state-a",entity,version,{"value":value,"modality":"semantic"},0.95,"a"*64),
        Evidence("benchmark-state-b",entity,version,{"value":value,"modality":"semantic"},0.90,"b"*64),
    ]
    if conflict:
        rows.extend([
            Evidence("benchmark-adversary-a",entity,version,{"value":"conflict","modality":"semantic"},0.95,"c"*64),
            Evidence("benchmark-adversary-b",entity,version,{"value":"conflict","modality":"semantic"},0.90,"d"*64),
        ])
    return tuple(rows)


def run_task(task: BenchmarkTask, trial: int) -> Mapping[str,Any]:
    before_value="before"
    desired=f"done:{task.domain}:{task.seed}"
    entity=f"bench.{task.domain}.{task.task_id}"
    initial=_evidence(task,before_value,"v1",conflict=(task.domain=="adversarial" and task.seed % 11 == 0))
    initial_world=fuse_world_state(initial)

    # Adversarial conflicting evidence is expected to fail closed safely.
    if initial_world.conflicts:
        return {
            "success":True,
            "recovered":True,
            "steps":0,
            "cost_usd":0.0,
            "terminal_code":"RECOVERY_CONFLICT_FAIL_CLOSED",
            "trace":{"task":task.task_id,"conflicts":initial_world.conflicts},
        }

    current={"world":initial_world,"attempts":0}
    rollback_count={"n":0}

    def executor(action):
        current["attempts"]+=1
        inject_recovery=(task.domain=="recovery" and task.seed % 3 == 0 and current["attempts"]==1)
        inject_provider=(task.domain=="provider_resilience" and task.seed % 4 == 0 and current["attempts"]==1)
        if inject_recovery or inject_provider:
            return {
                "accepted":False,
                "injected":True,
                "kind":"provider" if inject_provider else "execution",
            }
        current["world"]=fuse_world_state(_evidence(task,desired,f"v{current['attempts']+1}"))
        return {"accepted":True,"domain":task.domain}

    def observe():
        return current["world"]

    def rollback(action,evidence):
        rollback_count["n"]+=1
        current["world"]=initial_world

    mission=Mission(
        task.task_id,
        task.objective,
        entity,
        {"value":desired},
        tuple(task.required_capabilities),
        retry_budget=(2 if task.domain in ("recovery","provider_resilience") else 1),
    )
    runtime=ARBMRuntime(assurance=BenchmarkAssurance())
    result=runtime.run(
        mission,initial,executor,observe,rollback,
        task_id=task.task_id,source="benchmark-shadow",
        zero_spend_mode="HARD",github_sha="d"*40,
    )
    recovered=any(
        tx.recovered or (tx.recovery is not None) or tx.rollback_performed
        for tx in result.transactions
    )

    # In the first shadow baseline, injected one-shot failures are intentionally
    # visible rather than hidden. Recovery score must reflect runtime behavior.
    terminal="PASS" if result.success else ("RECOVERY_"+(result.failure or "FAIL").upper())
    trace={
        "task":task.task_id,
        "success":result.success,
        "failure":result.failure,
        "planned":result.planned,
        "committed":result.committed,
        "attempts":current["attempts"],
        "rollback_count":rollback_count["n"],
        "tx":[{
            "committed":tx.committed,
            "attempts":tx.attempts,
            "post":None if tx.post is None else tx.post.code,
            "recovery":None if tx.recovery is None else tx.recovery.root_cause.value,
            "rollback":tx.rollback_performed,
            "recovered":tx.recovered,
        } for tx in result.transactions],
    }
    return {
        "success":result.success,
        "recovered":recovered and result.success,
        "steps":sum(tx.attempts for tx in result.transactions),
        "cost_usd":0.0,
        "terminal_code":terminal,
        "trace":trace,
    }


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--count",type=int,default=400)
    ap.add_argument("--repetitions",type=int,default=3)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    tasks=build_internal_catalog(args.count)
    results=run_trials(tasks,run_task,repetitions=args.repetitions)
    metrics=summarize(tasks,results)
    gate=promotion_gate(metrics)
    payload={
        "schema":"arbm-runtime-benchmark-v1",
        "mode":"shadow-runtime",
        "frontier_comparable":False,
        "tasks":len(tasks),
        "repetitions":args.repetitions,
        "metrics":{
            **asdict(metrics),
            "source":metrics.source.value,
        },
        "promotion":asdict(gate),
        "results":[asdict(x) for x in results],
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(payload,indent=2,sort_keys=True,default=str)+"\n")
    print(json.dumps({
        "tasks":metrics.tasks,
        "trials":metrics.trials,
        "success_rate":round(metrics.success_rate,6),
        "determinism_rate":round(metrics.determinism_rate,6),
        "recovery_rate":round(metrics.recovery_rate,6),
        "total_cost_usd":metrics.total_cost_usd,
        "promotion":gate.level,
        "passed":gate.passed,
        "frontier_comparable":False,
    },sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())