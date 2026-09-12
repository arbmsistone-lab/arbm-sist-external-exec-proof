import json, sys
from pathlib import Path

root=Path('matrix-collected')
files=sorted(root.rglob('*.json'))
results=[json.loads(p.read_text(encoding='utf-8')) for p in files]
by={r['strategy']:r for r in results}
required={'foreground-proof','archive-lock','verified-noop','capacity-hold','planner-default','planner-mistral-first','planner-text-first','reviewer-advisory','policy-replan','build-parity'}
missing=sorted(required-set(by))
security=['foreground-proof','archive-lock','verified-noop','capacity-hold','reviewer-advisory','build-parity']
security_ok=not missing and all(bool(by[x].get('pass')) for x in security)

candidates=[]
weights={'planner-default':100,'planner-mistral-first':95,'planner-text-first':90,'policy-replan':85}
for name,weight in weights.items():
    r=by.get(name,{})
    if r.get('pass') and r.get('http')==200 and r.get('status')=='PASS':
        candidates.append((weight,name,r))
candidates.sort(reverse=True)
winner=candidates[0][1] if candidates else None
summary={'status':'V32_CLOUD_MATRIX_PASS' if security_ok and winner else 'V32_CLOUD_MATRIX_FAIL',
         'count':len(results),'missing':missing,'security_ok':security_ok,'winner':winner,
         'winner_result':by.get(winner) if winner else None,'results':results}
Path('v32-cloud-matrix-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary))
if not security_ok or not winner: sys.exit(1)
