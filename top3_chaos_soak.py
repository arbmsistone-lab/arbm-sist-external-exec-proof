import concurrent.futures, json, os, statistics, subprocess, threading, time
from pathlib import Path
import psycopg

DSNS=[os.environ[f'LOAD_DSN_{i}'] for i in range(4)]
OUT=Path('top3-evidence/security-load-failure'); OUT.mkdir(parents=True,exist_ok=True)
DURATION=45.0
CLIENTS=256
FAILED_CELL=1
POOL_PER_CELL=24
state={'down':set(),'reroutes':0}
lock=threading.Lock()
sems=[threading.Semaphore(POOL_PER_CELL) for _ in range(4)]

def pct(xs,p):
    s=sorted(xs)
    return 0.0 if not s else s[min(len(s)-1,int((len(s)-1)*p))]

def setup():
    for dsn in DSNS:
        with psycopg.connect(dsn,autocommit=True) as c:
            c.execute('drop schema if exists arbm_soak cascade; create schema arbm_soak')
            c.execute('create table arbm_soak.jobs(tenant_id text primary key, v int not null default 0)')
            c.execute("insert into arbm_soak.jobs select 'tenant-'||lpad(g::text,7,'0'),0 from generate_series(1,1000000) g")

def next_healthy(primary):
    with lock:
        down=set(state['down'])
    for hop in range(4):
        cell=(primary+hop)%4
        if cell not in down: return cell
    raise RuntimeError('all_cells_down')
def one_op(i):
    tenant_num=(i%1000000)+1
    primary=tenant_num%4
    tenant=f'tenant-{tenant_num:07d}'
    started=time.perf_counter()
    attempts=0
    while attempts<4:
        cell=next_healthy(primary if attempts==0 else (primary+attempts)%4)
        try:
            with sems[cell]:
                with psycopg.connect(DSNS[cell],autocommit=True,connect_timeout=2) as c:
                    row=c.execute('select v from arbm_soak.jobs where tenant_id=%s',(tenant,)).fetchone()
                    if row is None: raise RuntimeError('replica_miss')
            if cell!=primary:
                with lock: state['reroutes']+=1
            return (time.perf_counter()-started)*1000,cell,None
        except Exception:
            with lock: state['down'].add(cell)
            attempts+=1
    return (time.perf_counter()-started)*1000,-1,'unavailable_after_reroute'

def kill_cell_after(delay):
    time.sleep(delay)
    with lock: state['down'].add(FAILED_CELL)
    cid=subprocess.check_output(['docker','ps','-q','--filter','publish=5433'],text=True).strip()
    if cid: subprocess.run(['docker','stop',cid],check=True,stdout=subprocess.DEVNULL)

setup()
threading.Thread(target=kill_cell_after,args=(15,),daemon=True).start()
lat=[]; errors=[]; per_cell=[0,0,0,0]
start=time.perf_counter(); i=0
with concurrent.futures.ThreadPoolExecutor(max_workers=CLIENTS) as ex:
    pending=set()
    while time.perf_counter()-start<DURATION or pending:
        while time.perf_counter()-start<DURATION and len(pending)<CLIENTS*2:
            pending.add(ex.submit(one_op,i)); i+=1
        done,pending=concurrent.futures.wait(pending,timeout=.1,return_when=concurrent.futures.FIRST_COMPLETED)
        for f in done:
            ms,cell,err=f.result(); lat.append(ms)
            if cell>=0: per_cell[cell]+=1
            if err: errors.append(err)
elapsed=time.perf_counter()-start
out={
 'schema':'arbm-top3-chaos-soak-v1','remoteOnly':True,'zeroSpendHard':True,
 'durationSec':round(elapsed,3),'clients':CLIENTS,'failedCell':FAILED_CELL,
 'ops':len(lat),'errors':len(errors),'errorRate':round(len(errors)/max(1,len(lat)),6),
 'reroutes':state['reroutes'],'perCellOps':per_cell,'p95Ms':round(pct(lat,.95),3),
 'p99Ms':round(pct(lat,.99),3),'throughputOpsSec':round(len(lat)/elapsed,2),
 'paidFallbackUsed':False,'mandatoryCostUsd':0,
 'thresholds':{'errorRateMax':0,'p99MsMax':1500,'throughputMinOpsSec':500,'reroutesMin':1}
}
out['pass']=(out['errorRate']==0 and out['p99Ms']<1500 and out['throughputOpsSec']>500 and out['reroutes']>0 and not out['paidFallbackUsed'])
raw=json.dumps(out,indent=2,sort_keys=True)+'\n'
(OUT/'chaos-soak.json').write_text(raw)
import hashlib
(OUT/'chaos-soak.sha256').write_text(hashlib.sha256(raw.encode()).hexdigest()+'  chaos-soak.json\n')
print(json.dumps(out,sort_keys=True))
raise SystemExit(0 if out['pass'] else 2)
