import concurrent.futures, hashlib, json, os, queue, time
from pathlib import Path
import psycopg

DSN=os.environ.get('LOAD_DSN','postgresql://postgres:postgres@localhost:5432/loadtest')
OUT=Path('top3-evidence/security-load-failure'); OUT.mkdir(parents=True,exist_ok=True)
TENANTS=100000
POOL_SIZE=32
POOL=queue.LifoQueue(maxsize=POOL_SIZE)

def pct(xs,p):
    s=sorted(xs)
    if not s:return 0.0
    return s[min(len(s)-1,max(0,int(round((len(s)-1)*p))))]

def setup():
    with psycopg.connect(DSN,autocommit=True) as c:
        c.execute('drop schema if exists arbm_ceiling cascade; create schema arbm_ceiling')
        c.execute("create table arbm_ceiling.jobs(tenant_id text not null,idempotency_key text not null,state text not null default 'QUEUED',priority int not null default 0,primary key(tenant_id,idempotency_key))")
        t=time.perf_counter()
        c.execute("insert into arbm_ceiling.jobs(tenant_id,idempotency_key,priority) select 'tenant-'||lpad(g::text,6,'0'),'seed-'||g,(g%8) from generate_series(1,100000) g")
        seed_ms=(time.perf_counter()-t)*1000
        row=c.execute('select count(*),count(distinct tenant_id) from arbm_ceiling.jobs').fetchone()
    for _ in range(POOL_SIZE): POOL.put(psycopg.connect(DSN,autocommit=True))
    return {'rows':row[0],'distinctTenants':row[1],'seedMs':round(seed_ms,3),'poolSize':POOL_SIZE}
def one_op(i):
    tenant=f'tenant-{(i%TENANTS)+1:06d}'
    wait_t=time.perf_counter(); c=POOL.get(); wait_ms=(time.perf_counter()-wait_t)*1000
    try:
        t=time.perf_counter(); mode=i%10
        if mode<7:
            c.execute('select state,priority from arbm_ceiling.jobs where tenant_id=%s and idempotency_key=%s',(tenant,f'seed-{(i%TENANTS)+1}')).fetchone()
        elif mode<9:
            c.execute('update arbm_ceiling.jobs set priority=mod(priority+1,8) where tenant_id=%s and idempotency_key=%s',(tenant,f'seed-{(i%TENANTS)+1}'))
        else:
            c.execute('insert into arbm_ceiling.jobs(tenant_id,idempotency_key,priority) values(%s,%s,%s) on conflict do nothing',(tenant,f'burst-{i}',i%8))
        return (time.perf_counter()-t)*1000,wait_ms,None
    except Exception as e:
        return 0.0,wait_ms,type(e).__name__
    finally:
        POOL.put(c)

def stage(clients,ops):
    t=time.perf_counter(); lat=[]; waits=[]; errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=clients) as ex:
        for l,w,e in ex.map(one_op,range(ops)):
            if e: errors.append(e)
            else: lat.append(l)
            waits.append(w)
    elapsed=time.perf_counter()-t
    return {'clients':clients,'ops':ops,'completed':len(lat),'errors':len(errors),'errorRate':round(len(errors)/ops,6),'elapsedSec':round(elapsed,3),'throughputOpsSec':round(len(lat)/elapsed,2),'p95Ms':round(pct(lat,.95),3),'p99Ms':round(pct(lat,.99),3),'queueP95Ms':round(pct(waits,.95),3),'queueP99Ms':round(pct(waits,.99),3),'maxMs':round(max(lat) if lat else 0,3)}
seed=setup()
stages=[stage(16,4000),stage(64,8000),stage(128,12000)]
for _ in range(POOL_SIZE):
    try: POOL.get_nowait().close()
    except queue.Empty: break
pass_gate=(seed['rows']==TENANTS and seed['distinctTenants']==TENANTS and all(s['errors']==0 for s in stages) and all(s['p99Ms']<1000 for s in stages) and all(s['queueP99Ms']<2000 for s in stages) and stages[-1]['throughputOpsSec']>100)
out={'schema':'arbm-top3-load-ceiling-v1','remoteOnly':True,'zeroSpendHard':True,'seed':seed,'stages':stages,'thresholds':{'errorRateMax':0,'dbP99MsMax':1000,'queueP99MsMax':2000,'throughputMinOpsSec':100},'pass':pass_gate}
raw=json.dumps(out,indent=2,sort_keys=True)+'\n'
(OUT/'load-ceiling.json').write_text(raw)
(OUT/'load-ceiling.sha256').write_text(hashlib.sha256(raw.encode()).hexdigest()+'  load-ceiling.json\n')
print(json.dumps(out,sort_keys=True))
raise SystemExit(0 if pass_gate else 2)
