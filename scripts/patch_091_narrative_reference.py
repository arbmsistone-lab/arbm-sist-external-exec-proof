#!/usr/bin/env python3
from pathlib import Path

p=Path('scripts/osworld_local_vlm.py')
s=p.read_text(encoding='utf-8')
mark='ARBM_091_NARRATIVE_REFERENCE_RECOVERY_V1'
if mark in s:
    print('PATCH_091_NARRATIVE_REFERENCE=ALREADY_APPLIED'); raise SystemExit(0)

anchor="def parse_action_object(output, observation=''):\n"
insert=r'''# ARBM_091_NARRATIVE_REFERENCE_RECOVERY_V1
def _narrative_reference_action(raw, observation):
    text=str(raw or '')
    low=_norm(text)
    # Narrow recovery for the proven SmolVLM failure mode: repeated narrative
    # "The next step ..." with one unambiguous visible accessibility reference.
    if low.count('the next step') < 2:
        return None
    candidates=[]
    for item in _accessibility_targets(observation):
        label=str(item.get('label') or '').strip()
        norm=_norm(label)
        if len(norm) < 12 or norm not in low:
            continue
        candidates.append((len(norm),item))
    if not candidates:
        return None
    longest=max(x[0] for x in candidates)
    nodes={(x[1]['role'],x[1]['label'],x[1]['cx'],x[1]['cy']):x[1]
           for x in candidates if x[0]==longest}
    if len(nodes)!=1:
        raise ValueError('LOCAL_ACCESSIBILITY_TARGET_AMBIGUOUS')
    node=next(iter(nodes.values()))
    return {'action':'exec',
            'command':f"pyautogui.click({node['cx']}, {node['cy']})",
            'target':{'source':'accessibility','label':node['label'],'role':node['role']}}


'''
if anchor not in s: raise SystemExit('PARSE_ANCHOR_MISSING')
s=s.replace(anchor,insert+anchor,1)
old="""    natural=_natural_accessibility_action(raw,observation)\n    if natural:\n        return _compile_action(natural,observation)\n    raise ValueError('LOCAL_ACTION_REQUIRED')\n"""
new="""    natural=_natural_accessibility_action(raw,observation)\n    if natural:\n        return _compile_action(natural,observation)\n    narrative=_narrative_reference_action(raw,observation)\n    if narrative:\n        return _compile_action(narrative,observation)\n    raise ValueError('LOCAL_ACTION_REQUIRED')\n"""
if old not in s: raise SystemExit('PARSE_TAIL_MISSING')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')
print('PATCH_091_NARRATIVE_REFERENCE=PASS')
