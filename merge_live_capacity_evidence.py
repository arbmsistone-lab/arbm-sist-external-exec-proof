"""Merge live provider proofs into ephemeral capacity evidence, fail-closed."""
import argparse, json
from datetime import datetime, timezone
from mesh_capacity import _route_daily_units

REQUIRED_TRUE=("account_verified","recurring_free","reset_verified","no_paid_fallback")

def proof_units(p):
    kind=str(p.get("capacity_kind") or "tokens")
    useful=p.get("certified_useful_units_per_day")
    tokens=p.get("certified_tokens_per_day")
    if type(useful) is int and useful>0: return kind,useful,tokens if type(tokens) is int and tokens>=0 else 0
    if kind=="tokens" and type(tokens) is int and tokens>0: return kind,tokens,tokens
    return kind,0,0

def qualified(p):
    _,cap,_=proof_units(p)
    return (cap>0 and all(p.get(k) is True for k in REQUIRED_TRUE)
            and p.get("mandatory_cost_usd") in (0,0.0)
            and p.get("paid_fallback_used") is False
            and isinstance(p.get("independence_pool"),str) and bool(p["independence_pool"].strip()))

def to_route(p, run_id=""):
    kind,useful,tokens=proof_units(p)
    keys=("provider","independence_pool","account_verified","recurring_free","reset_verified","no_paid_fallback")
    route={k:p[k] for k in keys}; route["name"]=route.pop("provider")
    route.update({"mandatory_cost_usd":0,"paid_fallback_used":False,"capacity_kind":kind,
                  "certified_useful_units_per_day":useful,"certified_tokens_per_day":tokens})
    if isinstance(p.get("http"),int): route["live_probe_http"]=p["http"]
    route["evidence"]=[f"github-actions-run:{run_id}"] if run_id else ["live-provider-probe"]
    for k in ("model","models","documented_free_tokens_per_day","documented_free_tokens_per_model_day"):
        if k in p: route[k]=p[k]
    return route

def merge(baseline, probes, run_id=""):
    out=json.loads(json.dumps(baseline)); routes=list(out.get("routes",[]))
    pools={r.get("independence_pool"):i for i,r in enumerate(routes) if r.get("independence_pool")}
    for p in probes:
        if not qualified(p): continue
        route=to_route(p,run_id); pool=route["independence_pool"]
        if pool in pools:
            i=pools[pool]; _,old,_=_route_daily_units(routes[i])
            if route["certified_useful_units_per_day"]>int(old or 0): routes[i]=route
        else:
            pools[pool]=len(routes); routes.append(route)
    out["routes"]=routes
    useful=0; tokens=0
    for r in routes:
        _,u,t=_route_daily_units(r)
        if type(u) is int and u>0: useful+=u; tokens+=t
    target=int(out.get("target_useful_units_per_day",out.get("target_tokens_per_day",3_000_000)))
    out["certified_useful_units_per_day"]=useful; out["certified_tokens_per_day"]=tokens
    out["deficit_useful_units_per_day"]=max(0,target-useful)
    out["deficit_tokens_per_day"]=max(0,int(out.get("target_tokens_per_day",3_000_000))-tokens)
    out["status"]="PASS" if useful>=target else "FAIL"
    out["observed_at"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--baseline",required=True); ap.add_argument("--output",required=True)
    ap.add_argument("--probe",action="append",default=[]); ap.add_argument("--run-id",default=""); a=ap.parse_args()
    with open(a.baseline,encoding="utf-8") as f: baseline=json.load(f)
    probes=[]
    for path in a.probe:
        try:
            with open(path,encoding="utf-8") as f: probes.append(json.load(f))
        except (OSError,json.JSONDecodeError): pass
    out=merge(baseline,probes,a.run_id)
    with open(a.output,"w",encoding="utf-8") as f: json.dump(out,f,separators=(",",":"))
    active=set()
    for r in out["routes"]:
        _,u,_=_route_daily_units(r)
        if r.get("independence_pool") and type(u) is int and u>0 and all(r.get(k) is True for k in REQUIRED_TRUE): active.add(r["independence_pool"])
    print(json.dumps({"status":out["status"],"certified_useful_units_per_day":out["certified_useful_units_per_day"],"certified_tokens_per_day":out["certified_tokens_per_day"],"pools":len(active)},separators=(",",":")))

if __name__=="__main__": main()
