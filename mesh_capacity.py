"""Fail-closed account-specific capacity arithmetic; no network or price assumptions."""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_FLOOR
from math import ceil

UNKNOWN = "UNKNOWN"

def certify(account, now=None):
    fail = {"status": "FAIL_INSUFFICIENT_QUANTITATIVE_EVIDENCE", "certified_monthly_capacity": None,
            "remaining_certified_tokens": None, "safe_remaining_daily_budget": None}
    required = ("account_verified", "recurring_free", "payg_disabled", "shared_usage_accounted",
                "workspace_key_binding_verified", "model_price_binding_verified", "all_hard_limits_accounted",
                "no_paid_fallback", "throughput_sufficient")
    if any(account.get(k) is not True for k in required): return fail | {"reason": "account_evidence_incomplete"}
    numbers = ("tokens_per_month", "included_credit_usd", "input_price_per_million", "output_price_per_million",
               "other_hard_limit_tokens", "actual_usage_tokens", "other_usage_credit_usd", "safety_reserve")
    if any(type(account.get(k)) not in (int,float) or account[k] < 0 for k in numbers):
        return fail | {"reason": "quantitative_input_unknown"}
    try:
        values={k:Decimal(str(account[k])) for k in numbers}
        if not all(v.is_finite() for v in values.values()): return fail | {"reason":"nonfinite_input"}
        price=max(values["input_price_per_million"],values["output_price_per_million"])
        if price<=0: return fail | {"reason":"price_unknown"}
        credit=max(Decimal(0),values["included_credit_usd"]-values["other_usage_credit_usd"])
        economic=(credit*1000000/price).to_integral_value(rounding=ROUND_FLOOR)
        capacity=int(min(values["tokens_per_month"],economic,values["other_hard_limit_tokens"]))
        start=datetime.fromisoformat(account["cycle_start"].replace("Z","+00:00"))
        end=datetime.fromisoformat(account["cycle_end"].replace("Z","+00:00"))
        observed=datetime.fromisoformat(account["usage_observed_at"].replace("Z","+00:00"))
        now=now or datetime.now(timezone.utc)
        if any(t.tzinfo is None for t in [start,end,observed,now]) or not(start<=observed<=now<end):
            return fail | {"reason":"stale_cycle_or_usage"}
        if (now-observed).total_seconds()>300: return fail | {"reason":"stale_usage"}
        seconds=(end-start).total_seconds()
        if seconds<=0 or seconds%86400: return fail | {"reason":"ambiguous_cycle"}
        days=int(seconds/86400)
        if days not in (28,29,30,31): return fail | {"reason":"unsupported_cycle"}
        remaining=max(0,capacity-int(values["actual_usage_tokens"])-int(values["safety_reserve"]))
        remaining_days=ceil((end-now).total_seconds()/86400)
        daily=remaining//remaining_days
        required_cycle=3000000*days
        passed=capacity>=required_cycle and daily>=3000000
        return {"status":"PASS" if passed else "FAIL_INSUFFICIENT_CAPACITY", "certified_monthly_capacity":capacity,
                "required_cycle_capacity":required_cycle,"actual_days_in_billing_cycle":days,
                "remaining_days_in_cycle":remaining_days,"remaining_certified_tokens":remaining,
                "safe_remaining_daily_budget":daily,"economic_equivalent_not_standalone_proof":int(economic)}
    except (ValueError,KeyError,TypeError,ArithmeticError): return fail | {"reason":"invalid_account_evidence"}
