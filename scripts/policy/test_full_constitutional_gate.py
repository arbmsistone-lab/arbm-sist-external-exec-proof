#!/usr/bin/env python3
import hashlib,json,pathlib,subprocess,sys,tempfile

ROOT=pathlib.Path(__file__).resolve().parents[2]
GATE=ROOT/"scripts/policy/full_constitutional_gate.py"
MATRIX=ROOT/"policy/provider_failure_domains.json"
POLICY=ROOT/"policy/arbm_sist_constitution.json"

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
policy=json.loads(POLICY.read_text())

try:
    # The real matrix must satisfy exactly the constitution currently declared.
    current=run(manifest())
    if current.returncode!=0 or "PROMOTION_AUTHORITY=ALLOW" not in current.stdout:
        print(current.stdout)
        raise SystemExit("constitution-ready matrix did not allow complete evidence")
    print("CURRENT_CONSTITUTION_READY_MATRIX=ALLOW")

    # A benchmark regression must always force DENY.
    bad=manifest()
    bad["benchmarks"]["regression_tests"]["passed"]=False
    deny=run(bad)
    if deny.returncode==0 or "PROMOTION_AUTHORITY=ALLOW" in deny.stdout:
        raise SystemExit("regression failed open")
    print("NEGATIVE_REGRESSION_PATH=DENY")

    # For every critical capability, remove verified routes until it falls below
    # the declared independent-domain minimum and prove the gate fails closed.
    for cap,cfg in policy["critical_capabilities"].items():
        mutated=json.loads(original)
        verified=[
            r for r in mutated["routes"]
            if cap in r.get("capabilities",[]) and r.get("verified") is not False
        ]
        domains=[]
        for r in verified:
            if r["failure_domain"] not in domains:
                domains.append(r["failure_domain"])
        minimum=cfg["minimum_independent_routes"]
        if len(domains)<minimum:
            raise SystemExit(f"real matrix already underprovisioned:{cap}")
        keep=set(domains[:max(0,minimum-1)])
        for r in mutated["routes"]:
            if cap in r.get("capabilities",[]) and r.get("failure_domain") not in keep:
                r["verified"]=False
        MATRIX.write_text(json.dumps(mutated))
        r=run(manifest())
        if r.returncode==0 or f"failure_domains:{cap}" not in r.stdout:
            print(r.stdout)
            raise SystemExit(f"missing-route mutation failed open:{cap}")
        print(f"MUTATED_{cap.upper()}_UNDER_MINIMUM=DENY")

    print("ADVERSARIAL_FAIL_CLOSED_SELF_TEST=PASS")
finally:
    MATRIX.write_text(original)
