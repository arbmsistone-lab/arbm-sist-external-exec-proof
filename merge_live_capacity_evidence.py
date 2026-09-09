"""Merge live provider proofs into ephemeral capacity evidence, fail-closed."""
import argparse, json
from datetime import datetime, timezone

REQUIRED_TRUE=("account_verified","recurring_free","reset_verified","no_paid_fallback")

def qualified(p):
    cap=p.get("certified_tokens_per_day")
    return (type(cap) is int and cap>0 and all(p.get(k) is True for k in REQUIRED_TRUE)
            and p.get("mandatory_cost_usd") in (0,0.0)
            and p.get("paid_fallback_used") is False
            and isinstance(p.get("independence_pool"),str) and bool(p["independence_pool"].strip()))

def to_route(p, run_id=""):
    route={k:p[k] for k in ("provider","independence_pool","account_verified","recurring_free","reset_verified","no_paid_fallback","certified_tokens_per_day")}
    route["name"]=route.pop("provider")
    route["mandatory_cost_usd"]=0
    route["paid_fallback_used"]=False
    if isinstance(p.get("http"),int): route["live_probe_http"]=p["http"]
    route["evidence"]=[f"github-actions-run:{run_id}"] if run_id else ["live-provider-probe"]
    for k in ("model","models","documented_free_tokens_per_day","documented_free_tokens_per_model_day"):
        if k in p: route[k]=p[k]
    return route

def merge(baseline, probes, run_id=""):
    out=json.loads(json.dumps(baseline)); routes=list(out.get("routes",[])); pools={r.get("independence_pool"):i for i,r in enumerate(routes) if r.get("independence_pool")}
    for p in probes:
        if not qualified(p): continue
        route=to_route(p,run_id); pool=route["independence_pool"]
        if pool in pools:
            i=pools[pool]
            if route["certified_tokens_per_day"]>int(routes[i].get("certified_tokens_per_day",0)): routes[i]=route
        else:
            pools[pool]=len(routes); routes.append(route)
    out["routes"]=routes
    total=sum(int(r.get("certified_tokens_per_day",0)) for r in routes)
    target=int(out.get("target_tokens_per_day",3_000_000))
    out["certified_tokens_per_day"]=total
    out["deficit_tokens_per_day"]=max(0,target-total)
    out["status"]="PASS" if total>=target else "FAIL"
    out["observed_at"]=datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline",required=True); ap.add_argument("--output",required=True)
    ap.add_argument("--probe",action="append",default=[]); ap.add_argument("--run-id",default="")
    a=ap.parse_args()
    with open(a.baseline,encoding="utf-8") as f: baseline=json.load(f)
    probes=[]
    for path in a.probe:
        try:
            with open(path,encoding="utf-8") as f: probes.append(json.load(f))
        except (OSError,json.JSONDecodeError): pass
    out=merge(baseline,probes,a.run_id)
    with open(a.output,"w",encoding="utf-8") as f: json.dump(out,f,separators=(",",":"))
    active={r.get("independence_pool") for r in out["routes"] if r.get("independence_pool") and type(r.get("certified_tokens_per_day")) is int and r["certified_tokens_per_day"]>0 and all(r.get(k) is True for k in REQUIRED_TRUE)}
    print(json.dumps({"status":out["status"],"certified_tokens_per_day":out["certified_tokens_per_day"],"pools":len(active)},separators=(",",":")))

if __name__=="__main__": main()
