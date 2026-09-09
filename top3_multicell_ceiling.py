import concurrent.futures, hashlib, json, os, queue, time
from pathlib import Path
import psycopg

OUT=Path('top3-evidence/security-load-failure'); OUT.mkdir(parents=True,exist_ok=True)
TENANTS=1000000
CELLS=4
POOL_PER_CELL=32
DSNS=[os.environ[f'LOAD_DSN_{i}'] for i in range(CELLS)]
POOLS=[queue.LifoQueue(maxsize=POOL_PER_CELL) for _ in range(CELLS)]

def pct(xs,p):
    s=sorted(xs)
    if not s:return 0.0
    return s[min(len(s)-1,max(0,int(round((len(s)-1)*p))))]

def setup():
    started=time.perf_counter(); counts=[]
    for cell,dsn in enumerate(DSNS):
        with psycopg.connect(dsn,autocommit=True) as c:
            c.execute('drop schema if exists arbm_mc cascade; create schema arbm_mc')
            c.execute("create table arbm_mc.jobs(tenant_id text not null,idempotency_key text not null,state text not null default 'QUEUED',priority int not null default 0,primary key(tenant_id,idempotency_key))")
            c.execute("insert into arbm_mc.jobs(tenant_id,idempotency_key,priority) select 'tenant-'||lpad(g::text,7,'0'),'seed-'||g,(g%8) from generate_series(%s,%s) g",(cell*250000+1,(cell+1)*250000))
            counts.append(c.execute('select count(*) from arbm_mc.jobs').fetchone()[0])
        for _ in range(POOL_PER_CELL): POOLS[cell].put(psycopg.connect(dsn,autocommit=True))
    return {'rows':sum(counts),'cells':CELLS,'rowsPerCell':counts,'poolPerCell':POOL_PER_CELL,'seedMs':round((time.perf_counter()-started)*1000,3)}
def one_op(i):
    n=(i%TENANTS)+1; cell=(n-1)//250000; tenant=f'tenant-{n:07d}'
    wait_t=time.perf_counter(); c=POOLS[cell].get(); wait_ms=(time.perf_counter()-wait_t)*1000
    try:
        t=time.perf_counter(); mode=i%10
        if mode<7:
            c.execute('select state,priority from arbm_mc.jobs where tenant_id=%s and idempotency_key=%s',(tenant,f'seed-{n}')).fetchone()
        elif mode<9:
            c.execute('update arbm_mc.jobs set priority=mod(priority+1,8) where tenant_id=%s and idempotency_key=%s',(tenant,f'seed-{n}'))
        else:
            c.execute('insert into arbm_mc.jobs(tenant_id,idempotency_key,priority) values(%s,%s,%s) on conflict do nothing',(tenant,f'burst-{i}',i%8))
        return cell,(time.perf_counter()-t)*1000,wait_ms,None
    except Exception as e:
        return cell,0.0,wait_ms,type(e).__name__
    finally:
        POOLS[cell].put(c)

def stage(clients,ops):
    t=time.perf_counter(); lat=[]; waits=[]; errors=[]; per=[0]*CELLS
    with concurrent.futures.ThreadPoolExecutor(max_workers=clients) as ex:
        for cell,l,w,e in ex.map(one_op,range(ops)):
            per[cell]+=1; waits.append(w)
            if e: errors.append(e)
            else: lat.append(l)
    elapsed=time.perf_counter()-t
    return {'clients':clients,'ops':ops,'completed':len(lat),'errors':len(errors),'errorRate':round(len(errors)/ops,6),'elapsedSec':round(elapsed,3),'throughputOpsSec':round(len(lat)/elapsed,2),'p95Ms':round(pct(lat,.95),3),'p99Ms':round(pct(lat,.99),3),'queueP95Ms':round(pct(waits,.95),3),'queueP99Ms':round(pct(waits,.99),3),'perCellOps':per}
seed=setup()
stages=[stage(128,12000),stage(512,32000)]
for q in POOLS:
    while not q.empty(): q.get_nowait().close()
pass_gate=(seed['rows']==TENANTS and all(x==250000 for x in seed['rowsPerCell']) and all(s['errors']==0 for s in stages) and all(s['p99Ms']<1000 for s in stages) and all(s['queueP99Ms']<1000 for s in stages) and stages[-1]['throughputOpsSec']>1000)
out={'schema':'arbm-top3-multicell-ceiling-v1','remoteOnly':True,'zeroSpendHard':True,'seed':seed,'stages':stages,'thresholds':{'errorRateMax':0,'dbP99MsMax':1000,'queueP99MsMax':1000,'throughputMinOpsSec':1000},'pass':pass_gate}
raw=json.dumps(out,indent=2,sort_keys=True)+'\n'
(OUT/'multicell-ceiling.json').write_text(raw)
(OUT/'multicell-ceiling.sha256').write_text(hashlib.sha256(raw.encode()).hexdigest()+'  multicell-ceiling.json\n')
print(json.dumps(out,sort_keys=True))
raise SystemExit(0 if pass_gate else 2)
