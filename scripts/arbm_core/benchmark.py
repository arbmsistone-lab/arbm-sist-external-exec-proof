from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Any

@dataclass(frozen=True)
class BenchmarkCase:
    case_id: str
    domain: str
    run: Callable[[], bool]

@dataclass(frozen=True)
class BenchmarkReport:
    total: int
    passed: int
    failed: int
    by_domain: Mapping[str, Mapping[str,int]]

    @property
    def success_rate(self) -> float:
        return 1.0 if self.total == 0 else self.passed/self.total

def run_benchmark(cases: Iterable[BenchmarkCase]) -> BenchmarkReport:
    stats={}
    passed=0
    total=0
    for case in cases:
        total+=1
        ok=bool(case.run())
        passed+=int(ok)
        row=stats.setdefault(case.domain,{"passed":0,"failed":0})
        row["passed" if ok else "failed"]+=1
    return BenchmarkReport(total,passed,total-passed,stats)