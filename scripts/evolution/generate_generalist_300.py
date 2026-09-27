#!/usr/bin/env python3
import json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
domains={
"coding":["patch","debug","refactor","tests","dependency","api","cli","parser","serialization","concurrency"],
"tool_use":["file_read","file_write","search","git","process","artifact","workflow","api_call","routing","fallback"],
"recovery":["checkpoint","resume","retry","idempotency","lease","fencing","rollback","compensation","takeover","replay"],
"evidence":["hash","provenance","postcondition","artifact","log","world_state","binding","freshness","tamper","reproduce"],
"security":["least_privilege","secret_scope","injection","untrusted_input","network_policy","authz","sandbox","exfiltration","approval","audit"],
"planning":["decompose","dependency_graph","parallelize","replan","budget","stop_condition","definition_of_done","risk","priority","handoff"],
"computer_use":["observe","locate","click","type","save","verify_ui","recover_focus","dialog","scroll","screenshot"],
"multi_provider":["route","health","failover","shared_dependency","provider_loss","state_transfer","artifact_transfer","capability_match","degraded_mode","restore"],
"documents":["extract","transform","validate","layout","table","slide","spreadsheet","pdf","roundtrip","semantic_check"],
"data_reasoning":["filter","aggregate","compare","join","validate","outlier","schema","consistency","calculation","report"]
}
tasks=[];i=1
for domain,skills in domains.items():
 for skill in skills:
  for variant in ("nominal","faulted","adversarial"):
   tasks.append({"id":f"EVO-{i:04d}","domain":domain,"skill":skill,"variant":variant,"protected":True,"expected_evidence":["result","postcondition","provenance"],"zero_spend":True});i+=1
out={"schema_version":1,"suite":"ARBM-SIST-GENERALIST-300","task_count":len(tasks),"domains":len(domains),"tasks":tasks}
p=ROOT/"benchmarks/evolution/generalist-300.json";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2)+"\n")
print("TASKS="+str(len(tasks)));assert len(tasks)==300
