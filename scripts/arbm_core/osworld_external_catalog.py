#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from arbm_core.benchmark_program import import_external_catalog

PINNED_REPO="xlang-ai/OSWorld"
PINNED_SHA="b138d348256078fa634fc3b73567a7337c793e6b"
EXPECTED_TASKS=369

def load_catalog(root: Path):
    meta=json.loads((root/"evaluation_examples/test_all.json").read_text())
    rows=[]
    for domain,ids in meta.items():
        for tid in ids:
            cfg=root/"evaluation_examples/examples"/domain/f"{tid}.json"
            if not cfg.is_file():
                raise FileNotFoundError(cfg)
            data=json.loads(cfg.read_text())
            instruction=str(data.get("instruction") or "")
            if not instruction:
                raise ValueError(f"INSTRUCTION_MISSING:{domain}:{tid}")
            rows.append({
                "task_id":f"{domain}:{tid}",
                "domain":"multi_app" if domain=="multi_apps" else (
                    "coding" if domain=="vs_code" else
                    "office" if domain.startswith("libreoffice_") else
                    "web" if domain=="chrome" else
                    "gui"
                ),
                "instruction":instruction,
                "difficulty":3,
                "max_steps":100,
                "required_capabilities":["computer-use","grounding","verification"],
                "source_domain":domain,
                "source_task_id":tid,
                "config_sha256":hashlib.sha256(cfg.read_bytes()).hexdigest(),
            })
    if len(rows)!=EXPECTED_TASKS:
        raise ValueError(f"TASK_COUNT_MISMATCH:{len(rows)}")
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("osworld_root",type=Path)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    rows=load_catalog(args.osworld_root)
    tasks=import_external_catalog(rows,benchmark="osworld-verified-classic")
    payload={
        "schema":"arbm-external-benchmark-catalog-v1",
        "benchmark":"OSWorld/OSWorld-Verified classic",
        "repository":PINNED_REPO,
        "revision":PINNED_SHA,
        "frontier_comparable":True,
        "task_count":len(tasks),
        "tasks":[{
            "task_id":t.task_id,
            "domain":t.domain,
            "source":t.source.value,
            "objective":t.objective,
            "metadata":dict(t.metadata),
            "digest":t.digest,
        } for t in tasks],
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":"PASS","tasks":len(tasks),"revision":PINNED_SHA},sort_keys=True))
if __name__=="__main__":
    main()