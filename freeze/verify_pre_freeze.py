from pathlib import Path
import json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parent.parent
manifest=ROOT/"freeze"/"pre_freeze_manifest.json"
data=json.loads(manifest.read_text(encoding="utf-8"))
bad=[]
for e in data["files"]:
    p=ROOT/e["path"]
    if not p.exists():
        bad.append((e["path"],"MISSING"))
        continue
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    if h!=e["sha256"]:bad.append((e["path"],"HASH_MISMATCH"))
print(f"PRE_FREEZE_FILES={len(data['files'])}")
print(f"PRE_FREEZE_HASH_ERRORS={len(bad)}")
print("PRE_FREEZE_MANIFEST=PASS" if not bad else f"PRE_FREEZE_MANIFEST=FAIL {bad}")
raise SystemExit(0 if not bad else 1)
