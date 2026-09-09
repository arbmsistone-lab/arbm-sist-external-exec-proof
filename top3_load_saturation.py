import concurrent.futures, json, os, random, statistics, time
from pathlib import Path
import psycopg

DSN=os.environ.get('LOAD_DSN','postgresql://postgres:postgres@localhost:5432/loadtest')
OUT=Path('top3-evidence/security-load-failure'); OUT.mkdir(parents=True,exist_ok=True)

def pct(xs,p):
    s=sorted(xs)
    if not s:return 0.0
    i=min(len(s)-1,max(0,int(round((len(s)-1)*p))))
    return s[i]

def setup():
    with psycopg.connect(DSN,autocommit=True) as c:
        c.execute('drop schema if exists arbm_load cascade; create schema arbm_load')
        c.execute('create table arbm_load.jobs(tenant_id text not null,idempotency_key text not null,state text not null default \'QUEUED\',priority int not null default 0,payload jsonb not null default \'{}\'::jsonb,primary key(tenant_id,idempotency_key))')
        t=time.perf_counter()
        c.execute("insert into arbm_load.jobs(tenant_id,idempotency_key,priority) select 'tenant-'||lpad(g::text,5,'0'),'seed-'||g,(g%8) from generate_series(1,10000) g")
        seed_ms=(time.perf_counter()-t)*1000
        row=c.execute('select count(*),count(distinct tenant_id) from arbm_load.jobs').fetchone()
        return {'rows':row[0],'distinctTenants':row[1],'seedMs':round(seed_ms,3)}
def one_op(i):
    tenant=f'tenant-{(i%10000)+1:05d}'
    lat=[]; errors=[]
    try:
        with psycopg.connect(DSN,autocommit=True) as c:
            t=time.perf_counter()
            mode=i%10
            if mode<7:
                c.execute('select state,priority from arbm_load.jobs where tenant_id=%s and idempotency_key=%s',(tenant,f'seed-{(i%10000)+1}')).fetchone()
            elif mode<9:
                c.execute('update arbm_load.jobs set priority=(priority+1)%8 where tenant_id=%s and idempotency_key=%s',(tenant,f'seed-{(i%10000)+1}'))
            else:
                c.execute('insert into arbm_load.jobs(tenant_id,idempotency_key,priority) values(%s,%s,%s) on conflict do nothing',(tenant,f'burst-{i}',i%8))
            lat.append((time.perf_counter()-t)*1000)
    except Exception as e:
        errors.append(type(e).__name__)
    return lat,errors

def stage(clients,ops):
    t=time.perf_counter(); lat=[]; errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=clients) as ex:
        for ls,es in ex.map(one_op,range(ops)):
            lat.extend(ls); errors.extend(es)
    elapsed=time.perf_counter()-t
    return {'clients':clients,'ops':ops,'completed':len(lat),'errors':len(errors),'errorRate':round(len(errors)/ops,6),'elapsedSec':round(elapsed,3),'throughputOpsSec':round(len(lat)/elapsed,2),'p50Ms':round(pct(lat,.50),3),'p95Ms':round(pct(lat,.95),3),'p99Ms':round(pct(lat,.99),3),'maxMs':round(max(lat) if lat else 0,3)}
seed=setup()
stages=[stage(1,1000),stage(8,2000),stage(32,4000),stage(64,4000)]
pass_gate=(seed['rows']==10000 and seed['distinctTenants']==10000 and all(s['errors']==0 for s in stages) and all(s['p99Ms']<1000 for s in stages) and stages[-1]['throughputOpsSec']>100)
out={'schema':'arbm-top3-load-saturation-v1','remoteOnly':True,'zeroSpendHard':True,'seed':seed,'stages':stages,'thresholds':{'errorRateMax':0,'p99MsMax':1000,'saturatedThroughputMinOpsSec':100},'pass':pass_gate}
raw=json.dumps(out,indent=2,sort_keys=True)+'\n'
(OUT/'load-10k-saturation.json').write_text(raw)
import hashlib
(OUT/'load-10k-saturation.sha256').write_text(hashlib.sha256(raw.encode()).hexdigest()+'  load-10k-saturation.json\n')
print(json.dumps(out,sort_keys=True))
raise SystemExit(0 if pass_gate else 2)
