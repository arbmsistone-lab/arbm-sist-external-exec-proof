"""Fail-closed recurring FREE capacity revalidation gate."""
import json
from datetime import datetime, timezone
from pathlib import Path
from capacity_excellence import evidence_fresh
from mesh_capacity import certify_mesh
from capacity_excellence import chaos_floors

DEFAULT_TTL_HOURS=24
MIN_POOLS=5
MIN_N2=5_000_000

def check(evidence_path="account-capacity-evidence.json", now=None, live_revalidated=False):
    now=now or datetime.now(timezone.utc)
    d=json.loads(Path(evidence_path).read_text(encoding="utf-8-sig"))
    errors=[]
    if not live_revalidated and not evidence_fresh(d.get("observed_at"),now,DEFAULT_TTL_HOURS): errors.append("STALE_ROOT_EVIDENCE")
    mesh=certify_mesh(d.get("routes",[]),10_000_000)
    chaos=chaos_floors(d.get("routes",[]))
    if mesh["status"]!="PASS": errors.append("STRETCH_10M_NOT_PROVEN")
    if mesh["independent_pools"]<MIN_POOLS: errors.append("INSUFFICIENT_INDEPENDENT_POOLS")
    if chaos["n_plus_two_floor_useful_units_per_day"]<MIN_N2: errors.append("N_PLUS_TWO_MARGIN_BELOW_5M")
    for r in mesh["accepted_routes"]:
        if r["certified_useful_units_per_day"]<=0: errors.append("NONPOSITIVE_ACCEPTED_CAPACITY")
    return {"status":"PASS" if not errors else "FAIL","errors":errors,"mesh":mesh,"chaos":chaos}

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--live-revalidated',action='store_true'); a=ap.parse_args()
    out=check(live_revalidated=a.live_revalidated)
    print(json.dumps(out,separators=(',',':')))
    raise SystemExit(0 if out['status']=='PASS' else 2)
