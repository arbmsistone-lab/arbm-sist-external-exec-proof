"""Fail-closed account and mesh capacity certification.

Never derives daily capacity from TPM/RPM. Unknown evidence contributes zero.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from math import ceil

TARGET_TPD = 3_000_000
UNKNOWN = "UNKNOWN"


def _fail(reason):
    return {"status": "FAIL_INSUFFICIENT_QUANTITATIVE_EVIDENCE",
            "certified_monthly_capacity": None,
            "remaining_certified_tokens": None,
            "safe_remaining_daily_budget": None,
            "reason": reason}


def certify(account, now=None):
    required = ("account_verified", "recurring_free", "payg_disabled",
                "shared_usage_accounted", "workspace_key_binding_verified",
                "model_price_binding_verified", "all_hard_limits_accounted",
                "no_paid_fallback", "throughput_sufficient")
    if any(account.get(k) is not True for k in required):
        return _fail("account_evidence_incomplete")

    numbers = ("tokens_per_month", "included_credit_usd",
               "input_price_per_million", "output_price_per_million",
               "other_hard_limit_tokens", "actual_usage_tokens",
               "other_usage_credit_usd", "safety_reserve")
    if any(type(account.get(k)) not in (int, float) or account[k] < 0
           for k in numbers):
        return _fail("quantitative_input_unknown")
    try:
        values = {k: Decimal(str(account[k])) for k in numbers}
        if not all(v.is_finite() for v in values.values()):
            return _fail("nonfinite_input")
        price = max(values["input_price_per_million"],
                    values["output_price_per_million"])
        if price <= 0:
            return _fail("price_unknown")
        credit = max(Decimal(0), values["included_credit_usd"] -
                     values["other_usage_credit_usd"])
        economic = (credit * 1_000_000 / price).to_integral_value(
            rounding=ROUND_FLOOR)
        capacity = int(min(values["tokens_per_month"], economic,
                           values["other_hard_limit_tokens"]))

        start = datetime.fromisoformat(account["cycle_start"].replace("Z", "+00:00"))
        end = datetime.fromisoformat(account["cycle_end"].replace("Z", "+00:00"))
        observed = datetime.fromisoformat(account["usage_observed_at"].replace("Z", "+00:00"))
        now = now or datetime.now(timezone.utc)
        if any(t.tzinfo is None for t in (start, end, observed, now)):
            return _fail("timezone_missing")
        if not (start <= observed <= now < end):
            return _fail("stale_cycle_or_usage")
        if (now - observed).total_seconds() > 300:
            return _fail("stale_usage")
        seconds = (end - start).total_seconds()
        if seconds <= 0 or seconds % 86400:
            return _fail("ambiguous_cycle")
        days = int(seconds / 86400)
        if days not in (28, 29, 30, 31):
            return _fail("unsupported_cycle")
        remaining = max(0, capacity - int(values["actual_usage_tokens"]) -
                        int(values["safety_reserve"]))
        remaining_days = ceil((end - now).total_seconds() / 86400)
        daily = remaining // remaining_days
        required_cycle = TARGET_TPD * days
        passed = capacity >= required_cycle and daily >= TARGET_TPD
        return {"status": "PASS" if passed else "FAIL_INSUFFICIENT_CAPACITY",
                "certified_monthly_capacity": capacity,
                "required_cycle_capacity": required_cycle,
                "actual_days_in_billing_cycle": days,
                "remaining_days_in_cycle": remaining_days,
                "remaining_certified_tokens": remaining,
                "safe_remaining_daily_budget": daily,
                "economic_equivalent_not_standalone_proof": int(economic)}
    except (ValueError, KeyError, TypeError, ArithmeticError):
        return _fail("invalid_account_evidence")


def _route_daily_units(route):
    kind=str(route.get("capacity_kind") or "tokens")
    useful=route.get("certified_useful_units_per_day")
    tokens=route.get("certified_tokens_per_day")
    if type(useful) is int and useful >= 0:
        return kind, useful, tokens if type(tokens) is int and tokens >= 0 else 0
    if kind == "tokens" and type(tokens) is int and tokens >= 0:
        return kind, tokens, tokens
    return kind, None, 0


def certify_mesh(routes, target_tpd=TARGET_TPD):
    """Sum independent account-bound recurring useful capacity without conflating units."""
    total_units=0; token_total=0; accepted=[]; rejected=[]; seen_pools=set()
    for route in routes:
        name=str(route.get("name") or "unknown"); pool=str(route.get("independence_pool") or "")
        required=(route.get("account_verified") is True and route.get("recurring_free") is True and
                  route.get("no_paid_fallback") is True and route.get("reset_verified") is True and pool)
        kind,daily,tokens=_route_daily_units(route)
        if not required or daily is None:
            rejected.append({"name":name,"reason":"evidence_incomplete"}); continue
        if daily <= 0:
            rejected.append({"name":name,"reason":"zero_capacity"}); continue
        if pool in seen_pools:
            rejected.append({"name":name,"reason":"shared_pool_duplicate"}); continue
        seen_pools.add(pool); total_units += daily; token_total += tokens
        accepted.append({"name":name,"independence_pool":pool,"capacity_kind":kind,
                         "certified_useful_units_per_day":daily,"certified_tokens_per_day":tokens})
    return {"status":"PASS" if total_units >= target_tpd else "FAIL_INSUFFICIENT_CAPACITY",
            "target_useful_units_per_day":target_tpd,"certified_useful_units_per_day":total_units,
            "deficit_useful_units_per_day":max(0,target_tpd-total_units),
            "certified_tokens_per_day":token_total,"deficit_tokens_per_day":max(0,target_tpd-token_total),
            "accepted_routes":accepted,"rejected_routes":rejected,"independent_pools":len(seen_pools)}
