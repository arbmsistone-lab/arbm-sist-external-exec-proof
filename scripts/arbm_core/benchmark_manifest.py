#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from arbm_core.benchmark_program import build_internal_catalog

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--count",type=int,default=400)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    tasks=build_internal_catalog(args.count)
    payload={
        "schema":"arbm-benchmark-catalog-v1",
        "source":"internal",
        "frontier_comparable":False,
        "count":len(tasks),
        "tasks":[{
            "task_id":t.task_id,"domain":t.domain,"source":t.source.value,
            "objective":t.objective,"difficulty":t.difficulty,"seed":t.seed,
            "max_steps":t.max_steps,"required_capabilities":list(t.required_capabilities),
            "metadata":dict(t.metadata),"digest":t.digest,
        } for t in tasks],
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"PASS","count":len(tasks),"out":str(args.out)},sort_keys=True))

if __name__=="__main__":
    main()