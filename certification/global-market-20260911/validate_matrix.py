import json, pathlib, sys
p=pathlib.Path('certification/global-market-20260911/matrix.json')
d=json.loads(p.read_text(encoding='utf-8-sig'))
assert d['policy']=={'zero_spend':'HARD','heavy_local':0,'fail_closed':True,'no_regression':True}
assert d['release_gate']=='ALL_MANDATORY_GREEN'
ids=[x['id'] for x in d['mandatory']]
assert len(ids)==len(set(ids)) and {'terminal','web','tools','resilience','security','performance','integrity'}<=set(ids)
assert d['market_certified'] is False
print('GLOBAL_CERT_MATRIX_VALID=PASS')
print('MANDATORY_GATES='+str(len(ids)))
print('SPECIALIZATIONS='+str(len(d['specializations'])))
