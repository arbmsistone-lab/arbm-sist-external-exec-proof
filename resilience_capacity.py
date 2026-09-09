"""Fail-closed resilience certification for ARBM FREE useful capacity."""
from mesh_capacity import certify_mesh
BASE_TARGET_TPD=3_000_000; GROWTH_TARGET_TPD=5_000_000; STRETCH_TARGET_TPD=10_000_000

def certify_resilience(routes):
    base=certify_mesh(routes,BASE_TARGET_TPD); accepted=list(base["accepted_routes"])
    units=[r["certified_useful_units_per_day"] for r in accepted]
    largest=max(units,default=0); n1=max(0,base["certified_useful_units_per_day"]-largest)
    growth=certify_mesh(routes,GROWTH_TARGET_TPD); stretch=certify_mesh(routes,STRETCH_TARGET_TPD)
    return {"base_3m_status":base["status"],"certified_useful_units_per_day":base["certified_useful_units_per_day"],
            "certified_tokens_per_day":base["certified_tokens_per_day"],"independent_pools":base["independent_pools"],
            "largest_pool_useful_units_per_day":largest,"n_plus_one_floor_useful_units_per_day":n1,
            "n_plus_one_3m_status":"PASS" if n1>=BASE_TARGET_TPD else "FAIL_INSUFFICIENT_CAPACITY",
            "growth_5m_status":growth["status"],"growth_5m_deficit_useful_units_per_day":growth["deficit_useful_units_per_day"],
            "stretch_10m_status":stretch["status"],"stretch_10m_deficit_useful_units_per_day":stretch["deficit_useful_units_per_day"]}
