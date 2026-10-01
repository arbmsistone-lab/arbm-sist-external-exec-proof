from __future__ import annotations
from pathlib import Path
import random,hashlib,json

ROOT=Path(__file__).resolve().parent.parent
SEED=20261001
tasks=[f"T{i:02d}" for i in range(1,6)]
systems=["BASELINE","ARBM"]
rows=[]
for task in tasks:
    for rep in range(1,4):
        pair=systems[:]
        random.Random(f"{SEED}:{task}:{rep}").shuffle(pair)
        for system in pair:
            rows.append({"task":task,"rep":rep,"system":system})
payload=json.dumps(rows,separators=(",",":"),ensure_ascii=False).encode()
sha=hashlib.sha256(payload).hexdigest()
out={"RANDOMIZATION_SEED":SEED,"RUN_ORDER_SHA256":sha,"slots":rows,"secret_task_contents_included":False}
(ROOT/"randomization"/"run_order.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
print(f"RANDOMIZATION_SEED={SEED}")
print(f"RUN_ORDER_SHA256={sha}")
print(f"TOTAL_SLOTS={len(rows)}")
