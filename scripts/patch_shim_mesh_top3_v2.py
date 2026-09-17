#!/usr/bin/env python3
from pathlib import Path

source=Path('scripts/patch_shim_mesh_top3.py').read_text(encoding='utf-8')
old="once(nonce,nonce2,'FINAL_CAUSE')"
new="once(nonce,nonce + \"    if local_transient_cycles and provider_capacity_cycles==0:\\n        return terminal('LOCAL_FALLBACK_TRANSIENT_EXHAUSTED')\\n\",'FINAL_CAUSE')"
if old not in source:
    raise SystemExit('PATCH_V2_CONTEXT_MISSING')
source=source.replace(old,new,1)
exec(compile(source,'scripts/patch_shim_mesh_top3_v2.generated.py','exec'),{'__name__':'__main__'})
