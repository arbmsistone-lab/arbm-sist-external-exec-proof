#!/usr/bin/env python3
import json, sqlite3, time, threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

DB='/root/zevanory-state/state.db'
LOCK=threading.Lock()

def db():
    c=sqlite3.connect(DB, timeout=5, isolation_level=None)
    c.execute('PRAGMA journal_mode=WAL')
    c.execute('PRAGMA synchronous=FULL')
    c.execute('CREATE TABLE IF NOT EXISTS tasks(task_id TEXT PRIMARY KEY, operation_id TEXT, owner TEXT, lease_until REAL, checkpoint_id TEXT, last_committed_step TEXT, idempotency_key TEXT, attempt_id TEXT, resume_state TEXT, status TEXT, updated_at REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS effects(task_id TEXT, idempotency_key TEXT, effect_value TEXT, committed_at REAL, PRIMARY KEY(task_id,idempotency_key))')
    return c

def rowdict(cur,row):
    return dict(zip([d[0] for d in cur.description],row)) if row else None

class H(BaseHTTPRequestHandler):
    server_version='ZevanoryState/1.0'
    def log_message(self, fmt, *args): pass
    def sendj(self, code, obj):
        raw=json.dumps(obj,separators=(',',':')).encode()
        self.send_response(code); self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def body(self):
        n=int(self.headers.get('Content-Length','0')); raw=self.rfile.read(n) if n else b'{}'
        return json.loads(raw or b'{}')
    def do_GET(self):
        p=urlparse(self.path).path
        if p=='/health': return self.sendj(200,{'ok':True,'ts':time.time()})
        if p.startswith('/tasks/'):
            tid=p.split('/')[2]; c=db(); cur=c.execute('SELECT * FROM tasks WHERE task_id=?',(tid,)); r=rowdict(cur,cur.fetchone()); c.close()
            return self.sendj(200 if r else 404, r or {'error':'not_found'})
        return self.sendj(404,{'error':'not_found'})
    def do_POST(self):
        p=urlparse(self.path).path; parts=[x for x in p.split('/') if x]
        if len(parts)<3 or parts[0]!='tasks': return self.sendj(404,{'error':'not_found'})
        tid,action=parts[1],parts[2]; b=self.body(); now=time.time()
        with LOCK:
            c=db(); c.execute('BEGIN IMMEDIATE')
            try:
                cur=c.execute('SELECT * FROM tasks WHERE task_id=?',(tid,)); old=rowdict(cur,cur.fetchone())
                if action=='claim':
                    owner=b['owner']; lease=float(b.get('lease_seconds',60))
                    if old and old.get('lease_until',0)>now and old.get('owner')!=owner:
                        c.execute('ROLLBACK'); c.close(); return self.sendj(409,{'error':'lease_held','owner':old['owner'],'lease_until':old['lease_until']})
                    if old:
                        c.execute('UPDATE tasks SET owner=?,lease_until=?,attempt_id=?,updated_at=? WHERE task_id=?',(owner,now+lease,b.get('attempt_id'),now,tid))
                    else:
                        c.execute('INSERT INTO tasks(task_id,operation_id,owner,lease_until,idempotency_key,attempt_id,status,updated_at) VALUES(?,?,?,?,?,?,?,?)',(tid,b.get('operation_id'),owner,now+lease,b.get('idempotency_key'),b.get('attempt_id'),'RUNNING',now))
                elif action=='checkpoint':
                    if not old or old.get('owner')!=b.get('owner') or old.get('lease_until',0)<=now:
                        c.execute('ROLLBACK'); c.close(); return self.sendj(409,{'error':'not_owner'})
                    c.execute('UPDATE tasks SET checkpoint_id=?,last_committed_step=?,resume_state=?,idempotency_key=?,attempt_id=?,updated_at=? WHERE task_id=?',(b.get('checkpoint_id'),str(b.get('last_committed_step')),json.dumps(b.get('resume_state')),b.get('idempotency_key'),b.get('attempt_id'),now,tid))
                elif action=='effect':
                    if not old or old.get('owner')!=b.get('owner') or old.get('lease_until',0)<=now:
                        c.execute('ROLLBACK'); c.close(); return self.sendj(409,{'error':'not_owner'})
                    key=b['idempotency_key']
                    try:
                        c.execute('INSERT INTO effects(task_id,idempotency_key,effect_value,committed_at) VALUES(?,?,?,?)',(tid,key,json.dumps(b.get('value')),now)); duplicate=False
                    except sqlite3.IntegrityError:
                        duplicate=True
                    c.execute('COMMIT'); c.close(); return self.sendj(200,{'committed':not duplicate,'duplicate':duplicate})
                elif action=='complete':
                    if not old or old.get('owner')!=b.get('owner'):
                        c.execute('ROLLBACK'); c.close(); return self.sendj(409,{'error':'not_owner'})
                    c.execute('UPDATE tasks SET status=?,lease_until=0,resume_state=?,updated_at=? WHERE task_id=?',('COMPLETED',json.dumps(b.get('result')),now,tid))
                else:
                    c.execute('ROLLBACK'); c.close(); return self.sendj(404,{'error':'unknown_action'})
                c.execute('COMMIT'); cur=c.execute('SELECT * FROM tasks WHERE task_id=?',(tid,)); r=rowdict(cur,cur.fetchone()); c.close(); return self.sendj(200,r)
            except Exception as e:
                try: c.execute('ROLLBACK')
                except: pass
                c.close(); return self.sendj(500,{'error':type(e).__name__})

if __name__=='__main__':
    import os; os.makedirs('/root/zevanory-state',exist_ok=True); db().close()
    ThreadingHTTPServer(('100.97.108.80',8890),H).serve_forever()
