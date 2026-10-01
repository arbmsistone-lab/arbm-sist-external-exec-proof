from pathlib import Path
import json,hashlib,collections,sys
P=Path(__file__).with_name("run_order.json")
j=json.loads(P.read_text(encoding="utf-8"))
slots=j["slots"]
payload=json.dumps(slots,separators=(",",":"),ensure_ascii=False).encode()
sha=hashlib.sha256(payload).hexdigest()
counts=collections.Counter((x["task"],x["system"]) for x in slots)
pairs=collections.Counter((x["task"],x["rep"]) for x in slots)
ok=(len(slots)==30 and sha==j["RUN_ORDER_SHA256"] and
    all(counts[(f"T{i:02d}",s)]==3 for i in range(1,6) for s in ("BASELINE","ARBM")) and
    all(pairs[(f"T{i:02d}",r)]==2 for i in range(1,6) for r in range(1,4)))
print(f"TOTAL_SLOTS={len(slots)}")
print(f"RUN_ORDER_SHA256={sha}")
print(f"PAIR_BALANCE={'PASS' if ok else 'FAIL'}")
print("RANDOMIZATION_VERIFY=PASS" if ok else "RANDOMIZATION_VERIFY=FAIL")
raise SystemExit(0 if ok else 1)
