"""Fail-closed resilience certification for ARBM FREE capacity."""
from mesh_capacity import certify_mesh

BASE_TARGET_TPD = 3_000_000
GROWTH_TARGET_TPD = 5_000_000
STRETCH_TARGET_TPD = 10_000_000


def certify_resilience(routes):
    base = certify_mesh(routes, BASE_TARGET_TPD)
    accepted = list(base["accepted_routes"])
    capacities = [r["certified_tokens_per_day"] for r in accepted]
    largest = max(capacities, default=0)
    n1_floor = max(0, base["certified_tokens_per_day"] - largest)
    growth = certify_mesh(routes, GROWTH_TARGET_TPD)
    stretch = certify_mesh(routes, STRETCH_TARGET_TPD)
    n1_pass = n1_floor >= BASE_TARGET_TPD
    return {
        "base_3m_status": base["status"],
        "certified_tokens_per_day": base["certified_tokens_per_day"],
        "independent_pools": base["independent_pools"],
        "largest_pool_tokens_per_day": largest,
        "n_plus_one_floor_tokens_per_day": n1_floor,
        "n_plus_one_3m_status": "PASS" if n1_pass else "FAIL_INSUFFICIENT_CAPACITY",
        "growth_5m_status": growth["status"],
        "growth_5m_deficit_tokens_per_day": growth["deficit_tokens_per_day"],
        "stretch_10m_status": stretch["status"],
        "stretch_10m_deficit_tokens_per_day": stretch["deficit_tokens_per_day"],
    }

# Audit trigger: revalidate hardened capacity gates in cloud CI.
