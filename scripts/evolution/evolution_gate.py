#!/usr/bin/env python3
import argparse,json,pathlib,sys
ap=argparse.ArgumentParser();ap.add_argument("--candidate",required=True);ap.add_argument("--baseline-report",required=True);ap.add_argument("--candidate-report",required=True);a=ap.parse_args()
cfg=json.loads((pathlib.Path(__file__).resolve().parents[2]/"policy/evolution_program.json").read_text())
base=json.loads(pathlib.Path(a.baseline_report).read_text());cand=json.loads(pathlib.Path(a.candidate_report).read_text())
dims=cfg["benchmark_dimensions"]
def fail(x): print("EVOLUTION_PROMOTION=DENY",x);sys.exit(1)
for d in dims:
 if d not in base or d not in cand: fail("missing_dimension:"+d)
 if not isinstance(base[d],(int,float)) or not isinstance(cand[d],(int,float)): fail("non_numeric:"+d)
 if cand[d] < base[d]: fail("regression:"+d)
if cand.get("constitutional_pass") is not True: fail("constitution")
if cand.get("real_evidence") is not True: fail("real_evidence")
if cand.get("zero_spend") is not True: fail("zero_spend")
print("EVOLUTION_PROMOTION=ALLOW")
