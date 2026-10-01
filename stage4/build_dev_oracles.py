from pathlib import Path
from shutil import copy2
import json,hashlib
ROOT=Path(__file__).resolve().parent.parent
S4=ROOT/"stage4"; F=S4/"fixtures"; T=S4/"tasks"; A=S4/"attestations"
for d in (F,T,A):d.mkdir(parents=True,exist_ok=True)

def sha(p):
    h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()

# Development task 1: set Teclado quantity to 25
copy2(ROOT/"stage2/fixtures/bad.ods",F/"dev1_input.ods")
copy2(ROOT/"stage2/fixtures/good.ods",F/"dev1_expected.ods")
copy2(F/"dev1_expected.ods",F/"dev1_manual_output.ods")
task1={"task_id":"DEV-ORACLE-001","fixture":"stage4/fixtures/dev1_input.ods","expected_output":"stage4/fixtures/dev1_expected.ods",
"verifiers":[{"type":"cell_value_by_row_label","params":{"sheet":"Vendas","label_col":1,"label":"Teclado","target_col":2,"expected":25}}]}
(T/"dev1.json").write_text(json.dumps(task1,ensure_ascii=False,indent=2),encoding="utf-8")
att1={"mode":"DEVELOPMENT_ONLY","human_completed":True,"operator_confirmation":"I_COMPLETED_THIS_TASK_MANUALLY",
"fixture_sha256":sha(F/"dev1_input.ods"),"output_path":"stage4/fixtures/dev1_manual_output.ods","output_sha256":sha(F/"dev1_manual_output.ods")}
(A/"dev1_valid.json").write_text(json.dumps(att1,indent=2),encoding="utf-8")

# Negative attestations: no human confirmation / tampered hash / wrong output
bad=dict(att1); bad["human_completed"]=False; (A/"dev1_nohuman.json").write_text(json.dumps(bad,indent=2),encoding="utf-8")
bad=dict(att1); bad["fixture_sha256"]="0"*64; (A/"dev1_badhash.json").write_text(json.dumps(bad,indent=2),encoding="utf-8")
copy2(F/"dev1_input.ods",F/"dev1_wrong_output.ods")
bad=dict(att1); bad["output_path"]="stage4/fixtures/dev1_wrong_output.ods"; bad["output_sha256"]=sha(F/"dev1_wrong_output.ods")
(A/"dev1_wrongoutput.json").write_text(json.dumps(bad,indent=2),encoding="utf-8")
print("DEV_ORACLE_CASES_BUILT")
