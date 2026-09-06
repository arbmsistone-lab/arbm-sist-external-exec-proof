import json, os, re, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BACKEND=os.environ.get('ARBM_SOVEREIGN_BACKEND','http://127.0.0.1:8088')
PORT=int(os.environ.get('ARBM_SOVEREIGN_PROXY_PORT','8089'))
ACTION_RE=re.compile(r'```mswea_bash_command\s*\n(.*?)\n```',re.S)
BASH_RE=re.compile(r'```(?:bash|sh|shell)\s*\n(.*?)\n```',re.S|re.I)

def normalize(content):
    text=str(content or '')
    matches=ACTION_RE.findall(text)
    if matches:
        cmd=matches[0].strip()
    else:
        m=BASH_RE.search(text)
        cmd=m.group(1).strip() if m else 'pwd && git status --short && find . -maxdepth 2 -type f | head -80'
    if 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT' in cmd and len(matches)>1:
        cmd='git status --short && git diff --stat && git diff --check'
    return f'```mswea_bash_command\n{cmd}\n```'

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send_bytes(self,code,raw,ctype='application/json'):
        self.send_response(code); self.send_header('content-type',ctype)
        self.send_header('content-length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path in ('/health','/v1/health'):
            return self.send_bytes(200,b'{"status":"ok"}')
        return self.send_bytes(404,b'{"error":"not_found"}')

    def do_POST(self):
        if self.path!='/v1/chat/completions':
            return self.send_bytes(404,b'{"error":"not_found"}')
        size=int(self.headers.get('content-length','0') or 0)
        body=self.rfile.read(size)
        req=urllib.request.Request(BACKEND+self.path,data=body,method='POST')
        req.add_header('content-type','application/json')
        req.add_header('authorization',self.headers.get('authorization','Bearer local-dummy-key'))
        try:
            with urllib.request.urlopen(req,timeout=600) as res:
                data=json.loads(res.read())
            for choice in data.get('choices',[]):
                msg=choice.get('message') or {}
                msg['content']=normalize(msg.get('content',''))
                msg['tool_calls']=None
                choice['message']=msg
            raw=json.dumps(data).encode()
            return self.send_bytes(200,raw)
        except Exception as exc:
            raw=json.dumps({'error':{'message':str(exc),'type':'proxy_error'}}).encode()
            return self.send_bytes(502,raw)

if __name__=='__main__':
    ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
