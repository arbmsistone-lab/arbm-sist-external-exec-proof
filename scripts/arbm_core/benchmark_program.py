from __future__ import annotations
from dataclasses import dataclass, asdict
from enum import Enum
from statistics import mean
from typing import Callable, Iterable, Mapping, Any
import hashlib
import json
import time

class BenchmarkSource(str, Enum):
    INTERNAL="internal"
    EXTERNAL="external"

DOMAINS=(
    "gui",
    "web",
    "office",
    "coding",
    "multi_app",
    "recovery",
    "provider_resilience",
    "adversarial",
)

@dataclass(frozen=True)
class BenchmarkTask:
    task_id: str
    domain: str
    source: BenchmarkSource
    objective: str
    difficulty: int
    seed: int
    max_steps: int
    required_capabilities: tuple[str,...]
    metadata: Mapping[str,Any]

    def validate(self) -> None:
        if self.domain not in DOMAINS:
            raise ValueError("BENCHMARK_DOMAIN_INVALID:"+self.domain)
        if not self.task_id or not self.objective:
            raise ValueError("BENCHMARK_IDENTITY_REQUIRED")
        if not (1 <= self.difficulty <= 5):
            raise ValueError("BENCHMARK_DIFFICULTY_RANGE")
        if not (1 <= self.max_steps <= 200):
            raise ValueError("BENCHMARK_MAX_STEPS_RANGE")
        if self.source == BenchmarkSource.EXTERNAL:
            if not str(self.metadata.get("benchmark") or ""):
                raise ValueError("EXTERNAL_BENCHMARK_NAME_REQUIRED")
            if not str(self.metadata.get("external_task_id") or ""):
                raise ValueError("EXTERNAL_TASK_ID_REQUIRED")

    @property
    def digest(self) -> str:
        body=asdict(self)
        body["source"]=self.source.value
        body["required_capabilities"]=list(self.required_capabilities)
        return hashlib.sha256(json.dumps(body,sort_keys=True,default=str).encode()).hexdigest()

@dataclass(frozen=True)
class TrialResult:
    task_id: str
    trial: int
    success: bool
    recovered: bool
    steps: int
    cost_usd: float
    duration_ms: int
    terminal_code: str
    trace_digest: str

@dataclass(frozen=True)
class BenchmarkMetrics:
    source: BenchmarkSource
    tasks: int
    trials: int
    successes: int
    success_rate: float
    deterministic_tasks: int
    determinism_rate: float
    recovery_opportunities: int
    recovery_successes: int
    recovery_rate: float
    mean_steps: float
    total_cost_usd: float
    mean_duration_ms: float
    by_domain: Mapping[str,Mapping[str,float|int]]

@dataclass(frozen=True)
class PromotionDecision:
    passed: bool
    level: str
    reasons: tuple[str,...]

def build_internal_catalog(total: int=400) -> tuple[BenchmarkTask,...]:
    if total < len(DOMAINS) or total % len(DOMAINS):
        raise ValueError("INTERNAL_TOTAL_MUST_BE_BALANCED")
    per_domain=total//len(DOMAINS)
    tasks=[]
    for domain_index,domain in enumerate(DOMAINS):
        for i in range(per_domain):
            seed=domain_index*10000+i
            difficulty=1+(i % 5)
            task_id=f"internal.{domain}.{i+1:03d}"
            objective={
                "gui":"Manipulate a grounded desktop control and verify the semantic state transition.",
                "web":"Complete a browser workflow using grounded controls and explicit postconditions.",
                "office":"Edit structured office content and prove persistence without collateral changes.",
                "coding":"Apply a bounded source change and prove tests plus repository invariants.",
                "multi_app":"Complete a dependency-aware workflow across two applications with state handoff.",
                "recovery":"Recover from an injected execution failure without violating transaction guarantees.",
                "provider_resilience":"Complete a reasoning step after deterministic free-provider failure and failover.",
                "adversarial":"Reject or safely resolve ambiguous, stale, or conflicting observations.",
            }[domain]
            capabilities={
                "gui":("grounding","computer-use","verification"),
                "web":("browser","grounding","verification"),
                "office":("office","structured-state","rollback"),
                "coding":("git","tests","rollback"),
                "multi_app":("planning","multi-app","state-handoff"),
                "recovery":("root-cause","recovery","rollback"),
                "provider_resilience":("routing","zero-spend","failover"),
                "adversarial":("evidence-fusion","policy","fail-closed"),
            }[domain]
            tasks.append(BenchmarkTask(
                task_id,domain,BenchmarkSource.INTERNAL,objective,difficulty,seed,
                max_steps=20+difficulty*10,required_capabilities=capabilities,
                metadata={"catalog_version":"v1","synthetic":True,"frontier_comparable":False},
            ))
    for task in tasks:
        task.validate()
    return tuple(tasks)

def import_external_catalog(rows: Iterable[Mapping[str,Any]], *, benchmark: str) -> tuple[BenchmarkTask,...]:
    tasks=[]
    for i,row in enumerate(rows):
        domain=str(row.get("domain") or "gui")
        external_id=str(row.get("task_id") or row.get("id") or "")
        task=BenchmarkTask(
            task_id=f"external.{benchmark}.{external_id}",
            domain=domain,
            source=BenchmarkSource.EXTERNAL,
            objective=str(row.get("objective") or row.get("instruction") or "External benchmark task"),
            difficulty=int(row.get("difficulty") or 3),
            seed=int(row.get("seed") or i),
            max_steps=int(row.get("max_steps") or 100),
            required_capabilities=tuple(row.get("required_capabilities") or ("computer-use",)),
            metadata={
                "benchmark":benchmark,
                "external_task_id":external_id,
                "frontier_comparable":True,
                "source_record_digest":hashlib.sha256(json.dumps(dict(row),sort_keys=True,default=str).encode()).hexdigest(),
            },
        )
        task.validate()
        tasks.append(task)
    return tuple(tasks)

def run_trials(tasks: Iterable[BenchmarkTask],
               runner: Callable[[BenchmarkTask,int], Mapping[str,Any]],
               *, repetitions: int=3) -> tuple[TrialResult,...]:
    if repetitions < 2:
        raise ValueError("BENCHMARK_REPETITIONS_MIN_2")
    results=[]
    for task in tasks:
        task.validate()
        for trial in range(1,repetitions+1):
            started=time.monotonic()
            row=dict(runner(task,trial) or {})
            duration=int(row.get("duration_ms") or ((time.monotonic()-started)*1000))
            trace=json.dumps(row.get("trace") or {},sort_keys=True,default=str)
            results.append(TrialResult(
                task.task_id,trial,bool(row.get("success")),bool(row.get("recovered")),
                int(row.get("steps") or 0),float(row.get("cost_usd") or 0.0),duration,
                str(row.get("terminal_code") or ("PASS" if row.get("success") else "FAIL")),
                hashlib.sha256(trace.encode()).hexdigest(),
            ))
    return tuple(results)

def summarize(tasks: Iterable[BenchmarkTask], results: Iterable[TrialResult]) -> BenchmarkMetrics:
    task_rows={t.task_id:t for t in tasks}
    rs=list(results)
    if not rs:
        raise ValueError("BENCHMARK_RESULTS_REQUIRED")
    sources={task_rows[r.task_id].source for r in rs}
    if len(sources)!=1:
        raise ValueError("BENCHMARK_SOURCE_MIX_FORBIDDEN")
    source=next(iter(sources))
    grouped={}
    for r in rs:
        grouped.setdefault(r.task_id,[]).append(r)
    deterministic=sum(
        1 for rows in grouped.values()
        if len({(r.success,r.terminal_code,r.trace_digest) for r in rows})==1
    )
    recovery_ops=sum(1 for r in rs if r.terminal_code.startswith("RECOVERY_") or r.recovered)
    recovery_success=sum(1 for r in rs if r.recovered and r.success)
    by_domain={}
    for task_id,rows in grouped.items():
        domain=task_rows[task_id].domain
        d=by_domain.setdefault(domain,{"tasks":0,"trials":0,"successes":0})
        d["tasks"]+=1
        d["trials"]+=len(rows)
        d["successes"]+=sum(r.success for r in rows)
    for d in by_domain.values():
        d["success_rate"]=d["successes"]/d["trials"] if d["trials"] else 0.0
    return BenchmarkMetrics(
        source=source,tasks=len(grouped),trials=len(rs),
        successes=sum(r.success for r in rs),
        success_rate=sum(r.success for r in rs)/len(rs),
        deterministic_tasks=deterministic,
        determinism_rate=deterministic/len(grouped),
        recovery_opportunities=recovery_ops,
        recovery_successes=recovery_success,
        recovery_rate=(recovery_success/recovery_ops if recovery_ops else 1.0),
        mean_steps=mean(r.steps for r in rs),
        total_cost_usd=sum(r.cost_usd for r in rs),
        mean_duration_ms=mean(r.duration_ms for r in rs),
        by_domain=by_domain,
    )

def promotion_gate(metrics: BenchmarkMetrics, *, zero_spend: bool=True) -> PromotionDecision:
    reasons=[]
    if metrics.determinism_rate < 0.99:
        reasons.append(f"DETERMINISM_BELOW_99:{metrics.determinism_rate:.4f}")
    if metrics.recovery_rate < 0.95:
        reasons.append(f"RECOVERY_BELOW_95:{metrics.recovery_rate:.4f}")
    if zero_spend and metrics.total_cost_usd != 0.0:
        reasons.append(f"ZERO_SPEND_VIOLATION:{metrics.total_cost_usd:.6f}")
    if metrics.source == BenchmarkSource.INTERNAL:
        if metrics.success_rate < 0.95:
            reasons.append(f"INTERNAL_SUCCESS_BELOW_95:{metrics.success_rate:.4f}")
        level="INTERNAL_ELITE_CANDIDATE" if not reasons else "INTERNAL_NOT_READY"
    else:
        if metrics.tasks < 300:
            reasons.append(f"EXTERNAL_TASK_COUNT_BELOW_300:{metrics.tasks}")
        if metrics.success_rate < 0.80:
            reasons.append(f"EXTERNAL_SUCCESS_BELOW_80:{metrics.success_rate:.4f}")
        level="FRONTIER_CANDIDATE" if not reasons else "EXTERNAL_NOT_FRONTIER"
    return PromotionDecision(not reasons,level,tuple(reasons))