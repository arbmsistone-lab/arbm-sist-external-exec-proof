from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"stage4"))
from oracle_runner import run_oracle
T=ROOT/"stage4/tasks/dev1.json"; A=ROOT/"stage4/attestations"
cases=[
("valid_development_attestation",A/"dev1_valid.json",True),
("reject_missing_human",A/"dev1_nohuman.json",False),
("reject_fixture_hash_mismatch",A/"dev1_badhash.json",False),
("reject_wrong_output",A/"dev1_wrongoutput.json",False),
]
okn=0; fp=fn=0
for name,att,expected in cases:
    r=run_oracle(T,att); got=r["oracle_pass"]; ok=(got==expected); okn+=ok
    fp+=int(got and not expected); fn+=int((not got) and expected)
    print(f"{name}: EXPECTED={expected} GOT={got} {'PASS' if ok else 'FAIL'} {json.dumps(r,ensure_ascii=False)}")
print(f"ORACLE_CASES={okn}/{len(cases)}")
print(f"FALSE_POSITIVES={fp}")
print(f"FALSE_NEGATIVES={fn}")
gate=okn==len(cases) and fp==0 and fn==0
print("STAGE4_ORACLE_INFRA_GATE=PASS" if gate else "STAGE4_ORACLE_INFRA_GATE=FAIL")
print("SECRET_HUMAN_ORACLE_STATUS=PENDING_SECRET_TASK_CREATION")
sys.exit(0 if gate else 1)
