import json, os, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT=int(os.environ.get('ARBM_OIDC_BRIDGE_PORT','8090'))
REMOTE=os.environ['ARBM_REMOTE_ENDPOINT'].rstrip('/')
AUD='arbm-sist-benchmark'
OIDC_URL=os.environ['ACTIONS_ID_TOKEN_REQUEST_URL']
OIDC_REQ_TOKEN=os.environ['ACTIONS_ID_TOKEN_REQUEST_TOKEN']

def fresh_token():
    sep='&' if '?' in OIDC_URL else '?'
    req=urllib.request.Request(OIDC_URL+sep+'audience='+urllib.parse.quote(AUD))
    req.add_header('Authorization','bearer '+OIDC_REQ_TOKEN)
    with urllib.request.urlopen(req,timeout=20) as res:
        return json.loads(res.read())['value']

class H(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def sendb(self,code,raw,ctype='application/json'):
        self.send_response(code); self.send_header('content-type',ctype); self.send_header('content-length',str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path in ('/health','/v1/health'): return self.sendb(200,b'{"status":"ok"}')
        return self.sendb(404,b'{"error":"not_found"}')
    def do_POST(self):
        if self.path!='/v1/chat/completions': return self.sendb(404,b'{"error":"not_found"}')
        n=int(self.headers.get('content-length','0') or 0); body=self.rfile.read(n)
        try:
            token=fresh_token(); req=urllib.request.Request(REMOTE+'/v1/chat/completions',data=body,method='POST')
            req.add_header('content-type','application/json'); req.add_header('authorization','Bearer '+token)
            with urllib.request.urlopen(req,timeout=180) as res: raw=res.read(); code=res.status
            return self.sendb(code,raw)
        except urllib.error.HTTPError as e:
            return self.sendb(e.code,e.read())
        except Exception as e:
            return self.sendb(502,json.dumps({'error':'bridge_error','detail':str(e)[:200]}).encode())

if __name__=='__main__': ThreadingHTTPServer(('0.0.0.0',PORT),H).serve_forever()
