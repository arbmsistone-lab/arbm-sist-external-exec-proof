#!/usr/bin/env python3
import json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
p=json.loads((ROOT/"policy/global_route_fabric_candidate.json").read_text())
errors=[]
inv=p.get("invariants",{})
for k in ("NO_MANDATORY_PROVIDER","OPEN_ADAPTER_PROTOCOL","DYNAMIC_ROUTE_DISCOVERY","SURPLUS_ROUTE_CAPACITY"):
    if inv.get(k) is not True: errors.append(k)
if not p.get("provider_neutral"): errors.append("provider_neutral")
if p.get("hardcoded_provider_allowlist") is not False: errors.append("hardcoded_allowlist")
if p.get("provider_names_non_semantic") is not True: errors.append("provider_names_non_semantic")
proto=p.get("adapter_protocol",{})
expected=["DISCOVER","AUTHENTICATE","QUALIFY","LEASE","EXECUTE","OBSERVE","CHECKPOINT","VERIFY","RELEASE"]
if proto.get("lifecycle")!=expected: errors.append("adapter_lifecycle")
if proto.get("registration")!="dynamic": errors.append("dynamic_registration")
if proto.get("future_adapters_without_mission_kernel_change") is not True: errors.append("kernel_independence")
req=set(p.get("required_route_properties",[]))
need={"legitimate_authority","capability_match","health_pass","fresh_witness","dependency_graph","cost_policy_pass","security_policy_pass"}
if not need<=req: errors.append("route_admission")
crit=set(p.get("critical_route_properties",[]))
if not {"takeover_witness","independent_failure_domain"}<=crit: errors.append("critical_route_proof")
res=p.get("resilience",{})
if res.get("target_failure_domain_tolerance",0)<2: errors.append("failure_tolerance")
if res.get("required_spare_routes_after_tolerated_failures",0)<1: errors.append("no_spare_after_failures")
if res.get("shared_critical_dependency_collapses_routes") is not True: errors.append("dependency_collapse")
if p.get("unavailable_route_behavior")!="remove_from_eligible_quorum": errors.append("unavailable_behavior")
if p.get("rejoin_behavior")!="requalify_before_counting": errors.append("rejoin")
if errors:
 print("GLOBAL_ROUTE_FABRIC=FAIL "+",".join(errors));sys.exit(1)
for k in sorted(inv): print(f"{k}=PASS")
print("GLOBAL_ROUTE_FABRIC=PASS")
print("UNBOUNDED_ADAPTER_MODEL=PASS")
print("ALL_WORLD_ROUTES_LITERAL=NOT_CLAIMED")
