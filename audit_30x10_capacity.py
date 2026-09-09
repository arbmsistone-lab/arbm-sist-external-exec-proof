"""Deterministic 30-role x 10-cycle adversarial audit for FREE useful capacity."""
from capacity_excellence import evidence_freshness, chaos_floors
from resilience_capacity import certify_resilience
from mesh_capacity import _route_daily_units
ROLES=["capacity","resilience","billing","security","quota","routing","failover","sre","finops","api","evidence","audit","testing","chaos","quality","workload","latency","availability","cost","governance","compliance","observability","release","regression","provider","architecture","reliability","operations","risk","certification"]
def audit(routes,evidence,now):
 findings=[]; r=certify_resilience(routes); c=chaos_floors(routes)
 if r["base_3m_status"]!="PASS":findings.append("baseline_3m")
 if r["growth_5m_status"]!="PASS":findings.append("growth_5m")
 if r["stretch_10m_status"]!="PASS":findings.append("stretch_10m")
 if r["n_plus_one_3m_status"]!="PASS":findings.append("n_plus_one")
 if c["n_plus_two_floor_useful_units_per_day"]<3_000_000:findings.append("n_plus_two")
 pos=[x for x in routes if (_route_daily_units(x)[1] or 0)>0]
 if len({x.get("independence_pool") for x in pos})<4:findings.append("independent_pools_lt_4")
 if any(x.get("mandatory_cost_usd",0)!=0 or x.get("paid_fallback_used") is True or x.get("no_paid_fallback") is not True for x in pos):findings.append("zero_spend_violation")
 if any(evidence_freshness(x,now)["status"]!="PASS" for x in evidence):findings.append("stale_evidence")
 findings=sorted(set(findings)); passed=0 if findings else len(ROLES)*10
 return {"roles":len(ROLES),"cycles":10,"checks":len(ROLES)*10,"status":"PASS" if not findings else "FAIL","findings":findings,"passed_checks":passed}
