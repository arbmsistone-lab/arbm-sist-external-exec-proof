#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess,sys,tempfile

ROOT=pathlib.Path(__file__).resolve().parents[2]
GATE=ROOT/"scripts/policy/full_constitutional_gate.py"
MATRIX=ROOT/"policy/provider_failure_domains.json"

def H(s):
    return hashlib.sha256(s.encode()).hexdigest()

def manifest():
    c="a"*40
    b="b"*40
    return {
        "candidate_sha":c,
        "baseline_sha":b,
        "benchmarks":{
            k:{"candidate_sha":c,"passed":True}
            for k in ("contract_tests","regression_tests","adversarial_eval")
        },
        "evidence_ledger":[
            {"kind":"gate-self-test","sha256":H("x"),"source":"self-test"}
        ],
        "rollback":{"target_sha":b,"tested":True},
        "independent_verifier":{"passed":True},
        "promotion_authority":{"requested":True},
    }

def run(m):
    with tempfile.NamedTemporaryFile("w",suffix=".json",delete=False) as f:
        json.dump(m,f)
        p=f.name
    r=subprocess.run(
        [sys.executable,str(GATE),"--evidence",p],
        cwd=ROOT,text=True,capture_output=True
    )
    pathlib.Path(p).unlink(missing_ok=True)
    return r

original=MATRIX.read_text()
data=json.loads(original)

try:
    # Negative proof against the real matrix: with the fresh third compute route
    # intentionally unverified, a complete-looking manifest MUST be denied.
    current=run(manifest())
    if current.returncode==0:
        raise SystemExit("production evidence gap failed open")
    if "failure_domains:compute_execute" not in current.stdout:
        print(current.stdout)
        raise SystemExit("unexpected production deny reason")
    print("CURRENT_UNVERIFIED_THIRD_ROUTE=DENY")

    # Logic-positive fixture: temporarily qualify the declared candidate route
    # only inside this self-test to prove the gate can ALLOW after real evidence
    # changes its verified state. This does not alter production truth.
    candidates=[
        r for r in data["routes"]
        if r.get("id")=="circleci_candidate"
        and "compute_execute" in r.get("capabilities",[])
    ]
    if len(candidates)!=1:
        raise SystemExit("missing unique candidate compute route")
    candidates[0]["verified"]=True
    MATRIX.write_text(json.dumps(data))

    ok=run(manifest())
    if ok.returncode!=0 or "PROMOTION_AUTHORITY=ALLOW" not in ok.stdout:
        print(ok.stdout)
        raise SystemExit("qualified positive logic path failed")
    print("QUALIFIED_POSITIVE_LOGIC_PATH=ALLOW")

    # Regression mutation must still fail closed even after the synthetic route
    # qualification used above.
    bad=manifest()
    bad["benchmarks"]["regression_tests"]["passed"]=False
    deny=run(bad)
    if deny.returncode==0 or "PROMOTION_AUTHORITY=ALLOW" in deny.stdout:
        raise SystemExit("regression failed open")
    print("NEGATIVE_REGRESSION_PATH=DENY")

    # Remove a required source-control route from the qualified fixture and
    # prove the gate denies provider/failure-domain regression.
    candidates_sc=[
        r for r in data["routes"]
        if "source_control" in r.get("capabilities",[])
        and r.get("verified") is True
    ]
    if len(candidates_sc)<2:
        raise SystemExit("qualified fixture lacks source-control routes")
    candidates_sc[-1]["verified"]=False
    MATRIX.write_text(json.dumps(data))
    deny_missing=run(manifest())
    if deny_missing.returncode==0:
        raise SystemExit("missing-route mutation failed open")
    print("MUTATED_MISSING_ROUTE_PATH=DENY")
finally:
    MATRIX.write_text(original)
