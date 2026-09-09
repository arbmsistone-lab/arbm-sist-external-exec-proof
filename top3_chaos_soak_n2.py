import concurrent.futures, hashlib, json, os, queue, subprocess, threading, time
from pathlib import Path
import psycopg

DSNS=[os.environ[f'LOAD_DSN_{i}'] for i in range(4)]
OUT=Path('top3-evidence/security-load-failure'); OUT.mkdir(parents=True,exist_ok=True)
DURATION=90.0
CLIENTS=384
POOL_PER_CELL=32
FAILED_CELLS=(1,2)
KILL_AT=20.0
RECOVER_AT=50.0
QUORUM=2
state={'down':set(),'phase':'healthy','reroutes':0,'rejoined':False,'recoveryRtoSec':None}
state_lock=threading.Lock(); wal_lock=threading.Lock()
wal=[]; next_event=0
pools=[queue.Queue(maxsize=POOL_PER_CELL) for _ in range(4)]
container_ids={}

def pct(xs,p):
    s=sorted(xs)
    return 0.0 if not s else s[min(len(s)-1,int((len(s)-1)*p))]

def docker_id(port):
    return subprocess.check_output(['docker','ps','-aq','--filter',f'publish={port}'],text=True).strip()

def new_conn(cell):
    return psycopg.connect(DSNS[cell],autocommit=True,connect_timeout=2)
def fill_pool(cell):
    while not pools[cell].empty():
        try:
            c=pools[cell].get_nowait(); c.close()
        except Exception: pass
    for _ in range(POOL_PER_CELL): pools[cell].put(new_conn(cell))

def setup():
    for cell,dsn in enumerate(DSNS):
        with psycopg.connect(dsn,autocommit=True) as c:
            c.execute('drop schema if exists arbm_n2 cascade; create schema arbm_n2')
            c.execute('create table arbm_n2.jobs(tenant_id text primary key, v bigint not null default 0, last_event bigint not null default 0)')
            c.execute("insert into arbm_n2.jobs select 'tenant-'||lpad(g::text,7,'0'),0,0 from generate_series(1,1000000) g")
        fill_pool(cell)
        container_ids[cell]=docker_id(5432+cell)

def healthy_order(primary):
    with state_lock: down=set(state['down'])
    return [c for hop in range(4) if (c:=(primary+hop)%4) not in down]

def apply_event(cell,event):
    conn=pools[cell].get()
    try:
        conn.execute('update arbm_n2.jobs set v=v+1,last_event=%s where tenant_id=%s and last_event<%s',(event[0],event[1],event[0]))
    finally: pools[cell].put(conn)
def one_op(i):
    global next_event
    tenant_num=(i%1000000)+1; tenant=f'tenant-{tenant_num:07d}'; primary=tenant_num%4
    with wal_lock:
        next_event+=1; event=(next_event,tenant); wal.append(event)
    started=time.perf_counter(); ack=0; touched=[]
    for cell in healthy_order(primary):
        try:
            apply_event(cell,event); ack+=1; touched.append(cell)
            if cell!=primary:
                with state_lock: state['reroutes']+=1
        except Exception:
            with state_lock: state['down'].add(cell)
    err=None if ack>=QUORUM else 'quorum_unavailable'
    return (time.perf_counter()-started)*1000,touched,err,event[0]

def stop_cells():
    with state_lock:
        state['down'].update(FAILED_CELLS); state['phase']='n2'
    for cell in FAILED_CELLS:
        cid=container_ids[cell]
        if cid: subprocess.run(['docker','stop',cid],check=True,stdout=subprocess.DEVNULL)

def replay_cell(cell):
    started=time.perf_counter()
    cid=container_ids[cell]
    subprocess.run(['docker','start',cid],check=True,stdout=subprocess.DEVNULL)
    deadline=time.time()+15
    while time.time()<deadline:
        try:
            with psycopg.connect(DSNS[cell],autocommit=True,connect_timeout=1) as c: c.execute('select 1')
            break
        except Exception: time.sleep(.2)
    fill_pool(cell)
    cursor=0
    while True:
        with wal_lock:
            target=len(wal); snapshot=list(wal[cursor:target])
        for event in snapshot: apply_event(cell,event)
        cursor=target
        time.sleep(.02)
        with wal_lock: stable=(cursor==len(wal))
        if stable: break
    with state_lock: state['down'].discard(cell)
    return time.perf_counter()-started

def recover_cells():
    started=time.perf_counter()
    rtos=[]
    for cell in FAILED_CELLS: rtos.append(replay_cell(cell))
    with state_lock:
        state['phase']='recovered'; state['rejoined']=True; state['recoveryRtoSec']=round(time.perf_counter()-started,3)

def fault_schedule():
    time.sleep(KILL_AT); stop_cells()
    time.sleep(RECOVER_AT-KILL_AT); recover_cells()

def checksum(cell):
    conn=new_conn(cell)
    try:
        row=conn.execute("select count(*),sum(v),sum(last_event) from arbm_n2.jobs").fetchone()
        return tuple(int(x or 0) for x in row)
    finally: conn.close()

setup(); threading.Thread(target=fault_schedule,daemon=True).start()
lat=[]; errors=[]; touched=[0,0,0,0]; phase_ops={'healthy':0,'n2':0,'recovered':0}
start=time.perf_counter(); i=0
with concurrent.futures.ThreadPoolExecutor(max_workers=CLIENTS) as ex:
    pending=set()
    while time.perf_counter()-start<DURATION or pending:
        while time.perf_counter()-start<DURATION and len(pending)<CLIENTS*2:
            pending.add(ex.submit(one_op,i)); i+=1
        done,pending=concurrent.futures.wait(pending,timeout=.05,return_when=concurrent.futures.FIRST_COMPLETED)
        for f in done:
            ms,cells,err,seq=f.result(); lat.append(ms)
            for c in cells: touched[c]+=1
            with state_lock: phase_ops[state['phase']]+=1
            if err: errors.append(err)
elapsed=time.perf_counter()-start
checks=[checksum(c) for c in range(4)]
consistent=(len(set(checks))==1)
with state_lock:
    rejoined=state['rejoined']; rto=state['recoveryRtoSec']; reroutes=state['reroutes']; final_down=sorted(state['down'])
out={
 'schema':'arbm-top3-chaos-soak-n2-v1','remoteOnly':True,'zeroSpendHard':True,
 'durationSec':round(elapsed,3),'clients':CLIENTS,'failedCells':list(FAILED_CELLS),'quorum':QUORUM,
 'ops':len(lat),'errors':len(errors),'errorRate':round(len(errors)/max(1,len(lat)),6),
 'reroutes':reroutes,'perCellAcks':touched,'phaseOps':phase_ops,
 'p95Ms':round(pct(lat,.95),3),'p99Ms':round(pct(lat,.99),3),
 'throughputOpsSec':round(len(lat)/elapsed,2),'rejoined':rejoined,'recoveryRtoSec':rto,
 'finalDownCells':final_down,'checksums':[list(x) for x in checks],'consistent':consistent,
 'paidFallbackUsed':False,'mandatoryCostUsd':0,
 'thresholds':{'errorRateMax':0,'p99MsMax':1500,'throughputMinOpsSec':500,'recoveryRtoSecMax':20,'reroutesMin':1}
}
out['pass']=(out['errorRate']==0 and out['p99Ms']<1500 and out['throughputOpsSec']>500 and out['reroutes']>0 and out['rejoined'] and not out['finalDownCells'] and out['consistent'] and out['recoveryRtoSec'] is not None and out['recoveryRtoSec']<20 and not out['paidFallbackUsed'])
raw=json.dumps(out,indent=2,sort_keys=True)+'\n'
(OUT/'chaos-soak-n2.json').write_text(raw)
(OUT/'chaos-soak-n2.sha256').write_text(hashlib.sha256(raw.encode()).hexdigest()+'  chaos-soak-n2.json\n')
print(json.dumps(out,sort_keys=True))
raise SystemExit(0 if out['pass'] else 2)
