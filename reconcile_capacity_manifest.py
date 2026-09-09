import json
from pathlib import Path
p = Path('free-capacity-manifest.json')
d = json.loads(p.read_text(encoding='utf-8'))
d['as_of'] = '2026-09-09T20:40:06Z'
mi = d['live']['mistral']
mi['account_specific'] = True
mi['free_mode_admin_proven'] = False
mi['payg_disabled_proven'] = False
mi['daily_capacity_counted_for_gate'] = 0
mi['conservative_daily_capacity'] = 'UNKNOWN'
mi['reason'] = 'Live account-bound inference and zero mandatory cost are proven; organization Free-mode/PAYG state is not exposed by the standard API key, so no daily capacity is certified.'
mi['latest_live_run'] = 34402373100
op = d['live']['openrouter']
op['connected'] = False
op['live_qualified'] = False
op['account_specific'] = False
op['is_free_tier'] = None
op['certified_tokens_per_day'] = 0
op['daily_capacity_counted_for_gate'] = 0
op['reason'] = 'OPENROUTER_API_KEY is absent from the current proof repository; no current account-bound capacity is promotable.'
op['latest_probe_run'] = 34402373100
p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
