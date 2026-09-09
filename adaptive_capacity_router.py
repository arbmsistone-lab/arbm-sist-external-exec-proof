"""Deterministic ZERO_SPEND adaptive capacity router.

Routes only to currently eligible FREE pools. Failed, stale, exhausted or paid
routes are skipped. Selection is deterministic by health, remaining capacity
and configured priority; no provider is mandatory.
"""
from datetime import datetime, timezone

REQUIRED_TRUE=("account_verified","recurring_free","reset_verified","no_paid_fallback")

def eligible(route, now=None):
    now=now or datetime.now(timezone.utc)
    if not all(route.get(k) is True for k in REQUIRED_TRUE): return False
    if route.get("mandatory_cost_usd",0) != 0 or route.get("paid_fallback_used") is True: return False
    if route.get("healthy",True) is not True or route.get("quota_exhausted",False) is True: return False
    cooldown=route.get("cooldown_until")
    if cooldown:
        try:
            stamp=datetime.fromisoformat(str(cooldown).replace("Z","+00:00"))
            if stamp.tzinfo is None or stamp>now: return False
        except ValueError: return False
    cap=route.get("remaining_useful_units",route.get("certified_useful_units_per_day",route.get("certified_tokens_per_day",0)))
    return type(cap) is int and cap>0 and bool(str(route.get("independence_pool") or "").strip())

def rank(routes, now=None, exclude_pools=()):
    blocked=set(exclude_pools)
    rows=[]
    for route in routes:
        if route.get("independence_pool") in blocked or not eligible(route,now): continue
        remaining=route.get("remaining_useful_units",route.get("certified_useful_units_per_day",route.get("certified_tokens_per_day",0)))
        health=int(route.get("health_score",100)); priority=int(route.get("priority",100))
        rows.append((health,remaining,-priority,str(route.get("name","")),route))
    rows.sort(reverse=True,key=lambda x:x[:4])
    unique=[]; seen=set()
    for row in rows:
        pool=row[-1].get("independence_pool")
        if pool in seen: continue
        seen.add(pool); unique.append(row[-1])
    return unique

def choose(routes, now=None, exclude_pools=()):
    ranked=rank(routes,now,exclude_pools)
    return ranked[0] if ranked else None

def failover_chain(routes, now=None, max_hops=None):
    ranked=rank(routes,now)
    if max_hops is not None: ranked=ranked[:max(0,int(max_hops))]
    return [{"name":r.get("name"),"independence_pool":r.get("independence_pool"),
             "capacity_kind":r.get("capacity_kind","tokens"),
             "remaining_useful_units":r.get("remaining_useful_units",r.get("certified_useful_units_per_day",r.get("certified_tokens_per_day",0)))}
            for r in ranked]

def simulate_failover(routes, failed_pools=(), now=None):
    chain=failover_chain([r for r in routes if r.get("independence_pool") not in set(failed_pools)],now)
    return {"status":"PASS" if chain else "FAIL_NO_FREE_CAPACITY",
            "failed_pools":sorted(set(failed_pools)),"chain":chain,
            "selected":chain[0] if chain else None}
