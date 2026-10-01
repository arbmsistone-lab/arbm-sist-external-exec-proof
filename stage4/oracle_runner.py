from __future__ import annotations
from pathlib import Path
import json, hashlib, sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"stage2"))
sys.path.insert(0,str(ROOT/"stage3"))
from verifier_engine import verify
from integrity_checker import check_integrity

def sha256_file(p:Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def run_oracle(task_manifest, attestation_path):
    task=json.loads(Path(task_manifest).read_text(encoding="utf-8"))
    att=json.loads(Path(attestation_path).read_text(encoding="utf-8"))
    result={"task_id":task["task_id"],"mode":att.get("mode"),"human_attested":False,
            "fixture_hash_match":False,"output_hash_match":False,
            "target_verifier":False,"integrity":False,"oracle_pass":False}
    result["human_attested"]=bool(att.get("human_completed") is True and att.get("operator_confirmation")=="I_COMPLETED_THIS_TASK_MANUALLY")
    fixture=ROOT/task["fixture"]
    output=ROOT/att["output_path"]
    expected=ROOT/task["expected_output"]
    result["fixture_hash_match"]=(att.get("fixture_sha256")==sha256_file(fixture))
    result["output_hash_match"]=(att.get("output_sha256")==sha256_file(output))
    result["target_verifier"]=all(verify(output,s) for s in task["verifiers"])
    integ=check_integrity(final_path=output,expected_semantic_path=expected,target_verifier_pass=result["target_verifier"],expected_output_path=output)
    result["integrity"]=bool(integ["PASS"])
    result["oracle_pass"]=all([result["human_attested"],result["fixture_hash_match"],result["output_hash_match"],result["target_verifier"],result["integrity"]])
    return result

if __name__=="__main__":
    r=run_oracle(sys.argv[1],sys.argv[2]); print(json.dumps(r,ensure_ascii=False,indent=2)); sys.exit(0 if r["oracle_pass"] else 1)
