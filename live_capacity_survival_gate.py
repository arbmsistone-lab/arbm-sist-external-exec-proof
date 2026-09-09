"""Live degraded-mode survival gate for the ZERO_SPEND mesh.

Unavailable/exhausted providers are removed from routing rather than making the
whole mesh fail. The surviving live pools must still provide >=5M useful units/day.
"""
import argparse, json
from pathlib import Path

MIN_LIVE_USEFUL=5_000_000
MIN_LIVE_POOLS=3
POOL_BY_PROVIDER={
    'groq':'groq-organization','lightning':'lightning-account','cloudflare':'cloudflare-account',
    'mistral':'mistral-organization','supabase':'supabase-organization'}

def read_json(path):
    try: return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except Exception: return {}

def read_jsonl(path):
    rows=[]
    try:
        for line in Path(path).read_text(encoding='utf-8-sig').splitlines():
            try: rows.append(json.loads(line))
            except json.JSONDecodeError: pass
    except OSError: pass
    return rows

def account_live(rows, provider):
    aliases={'groq':{'groq','groq-json-object','groq-json-text'},'lightning':{'lightning','lightning-free'},'cloudflare':{'cloudflare'}}
    row=next((x for x in rows if x.get('provider_hint')==provider),None)
    if not row or row.get('http')!=200 or row.get('mandatory_cost_usd',0)!=0 or row.get('paid_fallback_used',False): return False
    return any(a.get('route') in aliases[provider] and a.get('status')==200 and a.get('parsed') is True for a in row.get('provider_attempts',[]))

def evaluate(evidence, account_rows, mistral, supabase):
    live={
        'groq':account_live(account_rows,'groq'),
        'lightning':account_live(account_rows,'lightning'),
        'cloudflare':account_live(account_rows,'cloudflare'),
        'mistral':mistral.get('status')=='PASS' and mistral.get('http')==200 and mistral.get('mandatory_cost_usd')==0 and mistral.get('paid_fallback_used') is False,
        'supabase':supabase.get('status')=='PASS' and supabase.get('http')==200 and supabase.get('mandatory_cost_usd')==0 and supabase.get('paid_fallback_used') is False,
    }
    capacities={r.get('independence_pool'):int(r.get('certified_useful_units_per_day',r.get('certified_tokens_per_day',0)) or 0) for r in evidence.get('routes',[])}
    active_pools={POOL_BY_PROVIDER[p] for p,ok in live.items() if ok}
    useful=sum(capacities.get(pool,0) for pool in active_pools)
    degraded=sorted(p for p,ok in live.items() if not ok)
    status='PASS' if useful>=MIN_LIVE_USEFUL and len(active_pools)>=MIN_LIVE_POOLS else 'FAIL'
    return {'status':status,'live_useful_units_per_day':useful,'live_pools':len(active_pools),
            'active_pools':sorted(active_pools),'degraded_providers':degraded,'provider_live':live,
            'min_live_useful_units_per_day':MIN_LIVE_USEFUL,'min_live_pools':MIN_LIVE_POOLS}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--evidence',default='account-capacity-evidence.json')
    ap.add_argument('--account',required=True); ap.add_argument('--mistral',required=True); ap.add_argument('--supabase',required=True)
    a=ap.parse_args(); evidence=read_json(a.evidence)
    out=evaluate(evidence,read_jsonl(a.account),read_json(a.mistral),read_json(a.supabase))
    print(json.dumps(out,separators=(',',':'))); return 0 if out['status']=='PASS' else 2

if __name__=='__main__': raise SystemExit(main())
