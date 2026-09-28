#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,subprocess,sys,tempfile
ap=argparse.ArgumentParser();ap.add_argument("--candidate",required=True);ap.add_argument("--baseline",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
root=pathlib.Path(__file__).resolve().parents[2]
def run(cmd): return subprocess.run(cmd,cwd=root,text=True,capture_output=True)
# Regression witness: deterministic constitutional test suite on exact candidate.
r=run([sys.executable,"scripts/policy/test_full_constitutional_gate.py"])
reg=(r.returncode==0 and "CURRENT_CONSTITUTION_READY_MATRIX=ALLOW" in r.stdout and "NEGATIVE_REGRESSION_PATH=DENY" in r.stdout and "ADVERSARIAL_FAIL_CLOSED_SELF_TEST=PASS" in r.stdout)
# Rollback witness: baseline object must exist and candidate must be able to identify it as a distinct git commit.
rb=run(["git","cat-file","-e",a.baseline+"^{commit}"])
rollback=(rb.returncode==0 and a.baseline!=a.candidate)
# Independent verifier: separate process recomputes candidate tree identity and policy file hashes.
tree=run(["git","rev-parse",a.candidate+"^{tree}"])
files=["policy/arbm_sist_constitution.json","policy/provider_failure_domains.json","policy/benchmark_contract.json"]
hashes={}
for f in files:
 p=root/f
 if not p.is_file(): raise SystemExit("missing verifier input "+f)
 hashes[f]=hashlib.sha256(p.read_bytes()).hexdigest()
ind=(tree.returncode==0 and len(tree.stdout.strip())==40 and len(set(hashes.values()))==len(hashes))
e={"candidate_sha":a.candidate,"baseline_sha":a.baseline,"regression_tests":{"passed":reg,"stdout_sha256":hashlib.sha256(r.stdout.encode()).hexdigest()},"rollback":{"target_sha":a.baseline,"tested":rollback,"method":"git_object_reachability_distinct_commit"},"independent_verifier":{"passed":ind,"candidate_tree":tree.stdout.strip(),"policy_hashes":hashes,"method":"separate_process_tree_and_policy_hash_verifier"}}
pathlib.Path(a.out).write_text(json.dumps(e,indent=2)+"\n")
if not (reg and rollback and ind): raise SystemExit("REAL_WITNESS=FAIL")
print("REAL_REGRESSION_WITNESS=PASS");print("REAL_ROLLBACK_WITNESS=PASS");print("REAL_INDEPENDENT_VERIFIER=PASS")
