"""Single fail-closed ceiling gate for ARBM FREE capacity."""
from capacity_excellence import chaos_floors, evidence_freshness
from resilience_capacity import certify_resilience

CEILING_TPD = 10_000_000


def certify_ceiling(routes, evidence, now):
    r = certify_resilience(routes)
    chaos = chaos_floors(routes)
    fresh = all(evidence_freshness(x, now)["status"] == "PASS" for x in evidence)
    criteria = {
        "baseline_3m": r["base_3m_status"] == "PASS",
        "growth_5m": r["growth_5m_status"] == "PASS",
        "stretch_10m": r["stretch_10m_status"] == "PASS",
        "n_plus_one_3m": chaos["n_plus_one_status"] == "PASS",
        "n_plus_two_3m": chaos["n_plus_two_status"] == "PASS",
        "evidence_fresh": fresh,
        "four_or_more_pools": r["independent_pools"] >= 4,
    }
    return {"status":"PASS" if all(criteria.values()) else "FAIL",
            "criteria":criteria,"certified_tokens_per_day":r["certified_tokens_per_day"],
            "n_plus_one_floor_tokens_per_day":chaos["n_plus_one_floor_tokens_per_day"],
            "n_plus_two_floor_tokens_per_day":chaos["n_plus_two_floor_tokens_per_day"]}
