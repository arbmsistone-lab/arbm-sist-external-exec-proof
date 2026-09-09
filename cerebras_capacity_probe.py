"""Fail closed: Cerebras current free offer is a temporary trial, not recurring FREE."""
import json
import os


def main():
    if os.environ.get("ZERO_SPEND_MODE") != "HARD":
        raise SystemExit("ZERO_SPEND_HARD_REQUIRED")
    key_present = bool(os.environ.get("CEREBRAS_API_KEY", "").strip())
    status = "REJECT_TEMPORARY_TRIAL_NOT_RECURRING" if key_present else "NOT_CONFIGURED"
    print(json.dumps({
        "provider": "cerebras", "status": status,
        "recurring_free": False, "temporary_trial": key_present,
        "mandatory_cost_usd": 0, "paid_fallback_used": False,
        "certified_tokens_per_day": 0,
        "reason": "current Free Trial is time-limited and cannot count as recurring FREE capacity",
    }, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())