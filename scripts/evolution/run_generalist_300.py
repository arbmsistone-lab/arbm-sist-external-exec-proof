#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from dataclasses import asdict
from pathlib import Path

from arbm_core.benchmark_program import BenchmarkSource,BenchmarkTask,run_trials,summarize,promotion_gate
from arbm_core.runtime_benchmark_runner import run_task

DOMAIN_MAP={
    "coding":"coding",
    "tool_use":"web",
    "recovery":"recovery",
    "evidence":"adversarial",
    "security":"adversarial",
    "planning":"multi_app",
    "computer_use":"gui",
    "multi_provider":"provider_resilience",
    "documents":"office",
    "data_reasoning":"multi_app",
}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--suite",type=Path,default=Path("benchmarks/evolution/generalist-300.json"))
    ap.add_argument("--repetitions",type=int,default=3)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()

    raw=json.loads(args.suite.read_text())
    rows=raw["tasks"]
    if len(rows)!=300:
        raise SystemExit("GENERALIST_300_CARDINALITY_INVALID")
    tasks=[]
    for idx,row in enumerate(rows):
        source_domain=row["domain"]
        if source_domain not in DOMAIN_MAP:
            raise SystemExit("GENERALIST_300_DOMAIN_UNMAPPED:"+source_domain)
        mapped=DOMAIN_MAP[source_domain]
        variant=row["variant"]
        if variant not in {"nominal","faulted","adversarial"}:
            raise SystemExit("GENERALIST_300_VARIANT_INVALID:"+variant)
        task=BenchmarkTask(
            task_id=row["id"],
            domain=mapped,
            source=BenchmarkSource.INTERNAL,
            objective=f"{source_domain}:{row['skill']}:{variant}",
            difficulty=3,
            seed=idx+1,
            max_steps=100,
            required_capabilities=(source_domain,row["skill"],variant),
            metadata={
                "suite":"ARBM-SIST-GENERALIST-300",
                "source_domain":source_domain,
                "skill":row["skill"],
                "variant":variant,
                "protected":bool(row["protected"]),
                "zero_spend":bool(row["zero_spend"]),
                "frontier_comparable":False,
            },
        )
        task.validate()
        tasks.append(task)

    results=run_trials(tasks,run_task,repetitions=args.repetitions)
    metrics=summarize(tasks,results)
    gate=promotion_gate(metrics)
    by_variant={}
    index={t.task_id:t for t in tasks}
    for r in results:
        v=index[r.task_id].metadata["variant"]
        d=by_variant.setdefault(v,{"trials":0,"successes":0})
        d["trials"]+=1
        d["successes"]+=int(r.success)
    for d in by_variant.values():
        d["success_rate"]=d["successes"]/d["trials"]

    payload={
        "schema":"arbm-generalist-300-runtime-v1",
        "suite":"ARBM-SIST-GENERALIST-300",
        "mode":"shadow-runtime",
        "frontier_comparable":False,
        "tasks":len(tasks),
        "trials":len(results),
        "repetitions":args.repetitions,
        "metrics":{**asdict(metrics),"source":metrics.source.value},
        "by_variant":by_variant,
        "promotion":asdict(gate),
        "results":[asdict(x) for x in results],
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(payload,indent=2,sort_keys=True,default=str)+"\n")
    print(json.dumps({
        "tasks":len(tasks),
        "trials":len(results),
        "success_rate":metrics.success_rate,
        "determinism_rate":metrics.determinism_rate,
        "recovery_rate":metrics.recovery_rate,
        "total_cost_usd":metrics.total_cost_usd,
        "by_variant":by_variant,
        "promotion":gate.level,
        "passed":gate.passed,
        "frontier_comparable":False,
    },sort_keys=True))
    return 0 if gate.passed else 1

if __name__=="__main__":
    raise SystemExit(main())
