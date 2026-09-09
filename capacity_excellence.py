"""Fail-closed excellence gates for ARBM FREE capacity."""
from datetime import datetime, timezone

EVIDENCE_TTL_HOURS = 24
BASE_TPD = 3_000_000


def evidence_fresh(observed_at, now=None, ttl_hours=EVIDENCE_TTL_HOURS):
    try:
        stamp = datetime.fromisoformat(str(observed_at).replace("Z", "+00:00"))
        now = now or datetime.now(timezone.utc)
        age = (now - stamp).total_seconds()
        return stamp.tzinfo is not None and 0 <= age <= ttl_hours * 3600
    except (TypeError, ValueError):
        return False


def monthly_governor(monthly_tokens, used_tokens, remaining_days, reserve_ratio=0.05):
    if any(type(v) not in (int, float) for v in (monthly_tokens, used_tokens, remaining_days, reserve_ratio)):
        return {"status":"FAIL","daily_budget":0}
    if monthly_tokens < 0 or used_tokens < 0 or remaining_days <= 0 or not 0 <= reserve_ratio < 1:
        return {"status":"FAIL","daily_budget":0}
    reserve = int(monthly_tokens * reserve_ratio)
    remaining = max(0, int(monthly_tokens) - int(used_tokens) - reserve)
    return {"status":"PASS","daily_budget":remaining // int(remaining_days),"reserve_tokens":reserve}


def chaos_floor(routes, failures=1):
    pools = {}
    for r in routes:
        if not all((r.get("account_verified") is True, r.get("recurring_free") is True,
                    r.get("no_paid_fallback") is True, r.get("reset_verified") is True)):
            continue
        pool = r.get("independence_pool"); cap = r.get("certified_tokens_per_day")
        if pool and type(cap) is int and cap >= 0:
            pools[pool] = max(pools.get(pool, 0), cap)
    ordered = sorted(pools.values(), reverse=True)
    floor = max(0, sum(ordered) - sum(ordered[:max(0, failures)]))
    return {"status":"PASS" if floor >= BASE_TPD else "FAIL_INSUFFICIENT_CAPACITY",
            "failures":failures,"surviving_tpd":floor,"independent_pools":len(pools)}

def evidence_freshness(item, now=None):
    stamp = item.get("observed_at") if isinstance(item, dict) else None
    ok = evidence_fresh(stamp, now)
    return {"status":"PASS" if ok else "FAIL_STALE_EVIDENCE","observed_at":stamp}


def chaos_floors(routes):
    n1 = chaos_floor(routes, 1)
    n2 = chaos_floor(routes, 2)
    return {"n_plus_one_floor_tokens_per_day":n1["surviving_tpd"],
            "n_plus_one_status":n1["status"],
            "n_plus_two_floor_tokens_per_day":n2["surviving_tpd"],
            "n_plus_two_status":n2["status"]}
