import json, pathlib
p=pathlib.Path('certification/global-market-20260911/virtual-expert-panel-50.json')
d=json.loads(p.read_text(encoding='utf-8-sig'))
errors=[]
experts=d.get('experts',[])
ids=[x.get('id') for x in experts]
if d.get('requiredExperts')!=50: errors.append('requiredExperts_not_50')
if len(experts)!=50: errors.append('expert_count_not_50')
if len(set(ids))!=50: errors.append('duplicate_ids')
if d.get('consensus')!='ALL_REQUIRED_PASS': errors.append('consensus')
if d.get('failClosed') is not True: errors.append('failClosed')
for e in experts:
    if not e.get('focus') or not e.get('role'): errors.append('missing_focus_or_role')
print(json.dumps({'pass':not errors,'observed':len(experts),'domains':sorted(set(e['focus'] for e in experts)),'errors':errors},indent=2))
raise SystemExit(1 if errors else 0)
