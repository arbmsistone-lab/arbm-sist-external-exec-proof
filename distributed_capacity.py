"""Fail-closed qualification for distributed, user-funded AI capacity."""

def qualify_user_pays(route):
    required = {
        "documented_user_pays": True,
        "developer_cost_zero": True,
        "per_user_isolation": True,
        "request_scoped_auth": True,
        "shared_developer_credential": False,
    }
    failed = [k for k, expected in required.items() if route.get(k) is not expected]
    if failed:
        return {
            "qualified": False,
            "mode": "USER_PAYS_BLOCKED",
            "failed": failed,
            "central_certified_tokens_per_day": 0,
        }
    return {
        "qualified": True,
        "mode": "USER_PAYS_DISTRIBUTED",
        "failed": [],
        "central_certified_tokens_per_day": 0,
        "developer_marginal_ai_cost": 0,
    }
