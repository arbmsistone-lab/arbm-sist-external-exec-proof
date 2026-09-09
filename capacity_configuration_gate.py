import json, os, sys
from pathlib import Path

def check(path='free-capacity-manifest.json'):
    d=json.loads(Path(path).read_text(encoding='utf-8'))
    live=d.get('live',{})
    errors=[]
    op=live.get('openrouter',{})
    has_or=bool(os.getenv('OPENROUTER_API_KEY','').strip())
    claims_or=bool(op.get('connected') or op.get('live_qualified') or op.get('account_specific') or int(op.get('certified_tokens_per_day') or 0)>0)
    if claims_or and not has_or: errors.append('OPENROUTER_CLAIM_WITHOUT_CURRENT_CREDENTIAL')
    if not has_or and int(op.get('daily_capacity_counted_for_gate') or 0)>0: errors.append('OPENROUTER_COUNTED_WITHOUT_CURRENT_CREDENTIAL')
    mi=live.get('mistral',{})
    if int(mi.get('daily_capacity_counted_for_gate') or 0)>0:
        if not mi.get('live_proven'): errors.append('MISTRAL_COUNTED_WITHOUT_LIVE_PROOF')
        if not mi.get('free_mode_admin_proven'): errors.append('MISTRAL_COUNTED_WITHOUT_FREE_MODE_PROOF')
        if not mi.get('payg_disabled_proven'): errors.append('MISTRAL_COUNTED_WITHOUT_PAYG_DISABLED_PROOF')
    return errors

if __name__=='__main__':
    errors=check(sys.argv[1] if len(sys.argv)>1 else 'free-capacity-manifest.json')
    print(json.dumps({'status':'PASS' if not errors else 'FAIL','errors':errors},separators=(',',':')))
    raise SystemExit(1 if errors else 0)
