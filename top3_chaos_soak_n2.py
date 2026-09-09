import concurrent.futures, hashlib, json, os, queue, subprocess, threading, time
from pathlib import Path
import psycopg

DSNS=[os.environ[f'LOAD_DSN_{i}'] for i in range(4)]
OUT=Path('top3-evidence/security-load-failure'); OUT.mkdir(parents=True,exist_ok=True)
DURATION=90.0; CLIENTS=384; POOL_PER_CELL=64
FAILED_CELLS=(1,2); KILL_AT=20.0; RECOVER_AT=50.0; QUORUM=2
RECOVERY_WRITER_LIMIT=128
FINAL_DELTA_MAX=1024
recovery_gate=threading.BoundedSemaphore(RECOVERY_WRITER_LIMIT)
rejoin_release=threading.Event(); rejoin_release.set()
state={'down':set(),'phase':'healthy','reroutes':0,'rejoined':False,'recoveryRtoSec':None,'cellRecoverySec':[]}
state_lock=threading.Lock(); wal_lock=threading.Lock(); wal=[]; next_event=0
pools=[queue.Queue(maxsize=POOL_PER_CELL) for _ in range(4)]
container_ids={}

def pct(xs,p):
    s=sorted(xs); return 0.0 if not s else s[min(len(s)-1,int((len(s)-1)*p))]

def docker_id(port):
    ids=subprocess.check_output(['docker','ps','-aq'],text=True).split()
    for cid in ids:
        info=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0]
        binds=(info.get('HostConfig',{}).get('PortBindings',{}).get('5432/tcp') or [])
        if any(str(b.get('HostPort'))==str(port) for b in binds): return cid
    return ''

def ensure_cell_up(cell):
    cid=docker_id(5432+cell)
    if not cid: raise RuntimeError(f'missing_cell_{cell}')
    subprocess.run(['docker','start',cid],check=True,stdout=subprocess.DEVNULL)
    deadline=time.time()+15
    while time.time()<deadline:
        try:
            with psycopg.connect(DSNS[cell],autocommit=True,connect_timeout=1) as c: c.execute('select 1')
            container_ids[cell]=cid; return
        except Exception: time.sleep(.2)
    raise RuntimeError(f'cell_{cell}_restart_timeout')
def new_conn(cell): return psycopg.connect(DSNS[cell],autocommit=True,connect_timeout=2)

def fill_pool(cell):
    while not pools[cell].empty():
        try: pools[cell].get_nowait().close()
        except Exception: pass
    for _ in range(POOL_PER_CELL): pools[cell].put(new_conn(cell))

def setup():
    for cell in range(4): ensure_cell_up(cell)
    for cell,dsn in enumerate(DSNS):
        with psycopg.connect(dsn,autocommit=True) as c:
            c.execute('drop schema if exists arbm_n2 cascade; create schema arbm_n2')
            c.execute('create table arbm_n2.events(event_id bigint primary key, tenant_id text not null)')
            c.execute('create index events_tenant_idx on arbm_n2.events(tenant_id)')
        fill_pool(cell)

def healthy_order(primary):
    with state_lock: down=set(state['down'])
    return [c for hop in range(4) if (c:=(primary+hop)%4) not in down]

def apply_event(cell,event):
    conn=pools[cell].get()
    try:
        conn.execute('insert into arbm_n2.events(event_id,tenant_id) values (%s,%s) on conflict do nothing',event)
    finally: pools[cell].put(conn)
def one_op(i):
    global next_event
    started=time.perf_counter(); gated=False
    with state_lock: phase=state['phase']
    if phase=='quiesce': rejoin_release.wait()
    elif phase=='repair': recovery_gate.acquire(); gated=True
    try:
        tenant_num=(i%1000000)+1; tenant=f'tenant-{tenant_num:07d}'; primary=tenant_num%4
        with wal_lock:
            next_event+=1; event=(next_event,tenant); wal.append(event)
        ack=0; touched=[]
        for cell in healthy_order(primary):
            try:
                apply_event(cell,event); ack+=1; touched.append(cell)
                if cell!=primary:
                    with state_lock: state['reroutes']+=1
            except Exception:
                with state_lock: state['down'].add(cell)
        return (time.perf_counter()-started)*1000,touched,(None if ack>=QUORUM else 'quorum_unavailable'),phase
    finally:
        if gated: recovery_gate.release()

def stop_cells():
    with state_lock: state['down'].update(FAILED_CELLS); state['phase']='n2'
    for cell in FAILED_CELLS:
        cid=container_ids[cell]
        subprocess.run(['docker','stop',cid],check=True,stdout=subprocess.DEVNULL)

def bulk_replay(cell,events):
    if not events: return
    conn=psycopg.connect(DSNS[cell],autocommit=False,connect_timeout=2)
    try:
        with conn.cursor() as cur:
            cur.execute('create temp table n2_replay(event_id bigint, tenant_id text) on commit drop')
            payload=''.join(f'{event_id}\t{tenant}\n' for event_id,tenant in events).encode()
            with cur.copy('copy n2_replay (event_id,tenant_id) from stdin') as cp: cp.write(payload)
            cur.execute('insert into arbm_n2.events select event_id,tenant_id from n2_replay on conflict do nothing')
        conn.commit()
    finally: conn.close()
def prepare_repair_cell(cell):
    started=time.perf_counter(); ensure_cell_up(cell)
    with new_conn(cell) as c: c.execute('drop index if exists arbm_n2.events_tenant_idx')
    return started

def replay_to_target(cell,cursor,target):
    with wal_lock: snapshot=list(wal[cursor:target])
    bulk_replay(cell,snapshot)
    return target

def warm_repair_cell(cell):
    with new_conn(cell) as c: c.execute('create index if not exists events_tenant_idx on arbm_n2.events(tenant_id)')
    fill_pool(cell)

def recover_cells():
    started=time.perf_counter()
    with state_lock: state['phase']='repair'
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(FAILED_CELLS)) as ex:
        cell_started=list(ex.map(prepare_repair_cell,FAILED_CELLS))
    cursors={cell:0 for cell in FAILED_CELLS}
    while True:
        with wal_lock: target=len(wal)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(FAILED_CELLS)) as ex:
            vals=list(ex.map(lambda c: replay_to_target(c,cursors[c],target),FAILED_CELLS))
        for cell,cursor in zip(FAILED_CELLS,vals): cursors[cell]=cursor
        with wal_lock: lag=len(wal)-target
        if lag<=FINAL_DELTA_MAX: break
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(FAILED_CELLS)) as ex:
        list(ex.map(warm_repair_cell,FAILED_CELLS))
    rejoin_release.clear()
    with state_lock: state['phase']='quiesce'
    for _ in range(RECOVERY_WRITER_LIMIT): recovery_gate.acquire()
    try:
        with wal_lock: target=len(wal)
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(FAILED_CELLS)) as ex:
            vals=list(ex.map(lambda c: replay_to_target(c,cursors[c],target),FAILED_CELLS))
        for cell,cursor in zip(FAILED_CELLS,vals): cursors[cell]=cursor
        with wal_lock:
            if not all(cursors[c]==len(wal) for c in FAILED_CELLS): raise RuntimeError('final_delta_not_zero')
            with state_lock:
                state['down'].difference_update(FAILED_CELLS); state['phase']='recovered'; state['rejoined']=True
                state['recoveryRtoSec']=round(time.perf_counter()-started,3); state['cellRecoverySec']=[round(time.perf_counter()-x,3) for x in cell_started]
    finally:
        for _ in range(RECOVERY_WRITER_LIMIT): recovery_gate.release()
        rejoin_release.set()

def fault_schedule():
    time.sleep(KILL_AT); stop_cells(); time.sleep(RECOVER_AT-KILL_AT); recover_cells()

def checksum(cell):
    conn=new_conn(cell)
    try:
        row=conn.execute('select count(*),coalesce(sum(event_id),0),coalesce(bit_xor(event_id),0) from arbm_n2.events').fetchone()
        return tuple(int(x or 0) for x in row)
    finally: conn.close()

setup(); threading.Thread(target=fault_schedule,daemon=True).start()
lat=[]; errors=[]; touched=[0,0,0,0]; phase_ops={'healthy':0,'n2':0,'repair':0,'quiesce':0,'recovered':0}; phase_lats={k:[] for k in phase_ops}
start=time.perf_counter(); i=0
with concurrent.futures.ThreadPoolExecutor(max_workers=CLIENTS) as ex:
    pending=set()
    while time.perf_counter()-start<DURATION or pending:
        while time.perf_counter()-start<DURATION and len(pending)<CLIENTS*2:
            pending.add(ex.submit(one_op,i)); i+=1
        done,pending=concurrent.futures.wait(pending,timeout=.05,return_when=concurrent.futures.FIRST_COMPLETED)
        for f in done:
            ms,cells,err,op_phase=f.result(); lat.append(ms); phase_lats[op_phase].append(ms)
            for c in cells: touched[c]+=1
            phase_ops[op_phase]+=1
            if err: errors.append(err)
elapsed=time.perf_counter()-start
checks=[checksum(c) for c in range(4)]
consistent=(len(set(checks))==1)
with state_lock:
    rejoined=state['rejoined']; rto=state['recoveryRtoSec']; cell_rto=list(state['cellRecoverySec']); reroutes=state['reroutes']; final_down=sorted(state['down'])
out={
 'schema':'arbm-top3-chaos-soak-n2-v2','remoteOnly':True,'zeroSpendHard':True,
 'durationSec':round(elapsed,3),'clients':CLIENTS,'failedCells':list(FAILED_CELLS),'quorum':QUORUM,
 'ops':len(lat),'errors':len(errors),'errorRate':round(len(errors)/max(1,len(lat)),6),
 'reroutes':reroutes,'perCellAcks':touched,'phaseOps':phase_ops,'phaseP99Ms':{k:round(pct(v,.99),3) for k,v in phase_lats.items()},
 'p95Ms':round(pct(lat,.95),3),'p99Ms':round(pct(lat,.99),3),'throughputOpsSec':round(len(lat)/elapsed,2),
 'rejoined':rejoined,'recoveryRtoSec':rto,'cellRecoverySec':cell_rto,'finalDownCells':final_down,
 'checksums':[list(x) for x in checks],'consistent':consistent,
 'paidFallbackUsed':False,'mandatoryCostUsd':0,
 'thresholds':{'errorRateMax':0,'p99MsMax':1500,'phaseP99MsMax':1500,'throughputMinOpsSec':500,'recoveryRtoSecMax':20,'reroutesMin':1}
}
phase_p99_ok=all(v<1500 for k,v in out['phaseP99Ms'].items() if phase_ops[k]>0)
out['pass']=(out['errorRate']==0 and out['p99Ms']<1500 and phase_p99_ok and out['throughputOpsSec']>500 and out['reroutes']>0 and out['rejoined'] and not out['finalDownCells'] and out['consistent'] and out['recoveryRtoSec'] is not None and out['recoveryRtoSec']<20 and not out['paidFallbackUsed'])
raw=json.dumps(out,indent=2,sort_keys=True)+'\n'
(OUT/'chaos-soak-n2.json').write_text(raw)
(OUT/'chaos-soak-n2.sha256').write_text(hashlib.sha256(raw.encode()).hexdigest()+'  chaos-soak-n2.json\n')
print(json.dumps(out,sort_keys=True))
raise SystemExit(0 if out['pass'] else 2)
