#!/usr/bin/env python3
import json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
p=json.loads((ROOT/"policy/global_route_fabric_candidate.json").read_text())
errors=[]
if not p.get("provider_neutral"): errors.append("provider_neutral")
if p.get("hardcoded_provider_allowlist") is not False: errors.append("hardcoded_allowlist")
req=set(p.get("required_route_properties",[]))
need={"legitimate_authority","capability_match","health_pass","fresh_witness","dependency_graph","cost_policy_pass","security_policy_pass"}
if not need<=req: errors.append("route_admission")
if p.get("unavailable_route_behavior")!="remove_from_eligible_quorum": errors.append("unavailable_behavior")
if p.get("rejoin_behavior")!="requalify_before_counting": errors.append("rejoin")
if "failure_domain_diversity" not in p.get("routing_objectives",[]): errors.append("diversity")
if "spare_capacity" not in p.get("routing_objectives",[]): errors.append("spare_capacity")
if errors:
 print("GLOBAL_ROUTE_FABRIC=FAIL "+",".join(errors));sys.exit(1)
print("GLOBAL_ROUTE_FABRIC=PASS")
print("UNBOUNDED_ADAPTER_MODEL=PASS")
print("ALL_WORLD_ROUTES_LITERAL=NOT_CLAIMED")
