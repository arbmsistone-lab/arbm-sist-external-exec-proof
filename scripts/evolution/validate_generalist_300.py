#!/usr/bin/env python3
import json,pathlib,collections,sys
ROOT=pathlib.Path(__file__).resolve().parents[2];p=ROOT/"benchmarks/evolution/generalist-300.json"
d=json.loads(p.read_text());tasks=d["tasks"]
if len(tasks)!=300 or len({x["id"] for x in tasks})!=300:raise SystemExit("suite cardinality/id failure")
domains=collections.Counter(x["domain"] for x in tasks);variants=collections.Counter(x["variant"] for x in tasks)
if len(domains)!=10 or any(v!=30 for v in domains.values()):raise SystemExit("domain balance failure")
if any(variants[v]!=100 for v in ("nominal","faulted","adversarial")):raise SystemExit("variant balance failure")
if not all(x["protected"] and x["zero_spend"] and len(x["expected_evidence"])>=3 for x in tasks):raise SystemExit("protection/evidence failure")
print("GENERALIST_300_SCHEMA=PASS");print("DOMAINS="+str(dict(domains)));print("VARIANTS="+str(dict(variants)))
