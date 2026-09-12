import json, types
from pathlib import Path
src=Path(__file__).with_name('osworld_free_mesh_shim.py').read_text(encoding='utf-8')
src=src.rsplit('ThreadingHTTPServer(("127.0.0.1", 8088), Handler).serve_forever()',1)[0]
ns={}
exec(compile(src,'shim','exec'),ns)
class R:
    def __init__(self,status,data): self.status=status; self.data=data
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def read(self): return json.dumps(self.data).encode()
seq=[('http_error',422,{'status':'INVALID_ACTION'}),('ok',200,{'ok':True,'status':'PASS','pipeline':ns['EXPECTED_PIPELINE'],'agent_build':ns['EXPECTED_BUILD'],'action':{'action':'exec','command':"pyautogui.press('enter')"}})]
def fake(req,timeout=0):
    kind,status,data=seq.pop(0)
    if kind=='ok': return R(status,data)
    e=ns['urllib'].error.HTTPError(req.full_url,status,'x',{},None); e.read=lambda: json.dumps(data).encode(); raise e
ns['oidc_token']=lambda:'x'; ns['urllib'].request.urlopen=fake; ns['time'].sleep=lambda *_:None
msgs=[{'role':'system','content':'You are asked to complete the following task: press enter'},{'role':'user','content':[{'type':'text','text':'obs'},{'type':'image_url','image_url':{'url':'data:image/png;base64,AA=='}}]}]
out=ns['call_mesh'](msgs)
assert out=="```python\npyautogui.press('enter')\n```",out
ns['STATE']['no_progress']=ns['MAX_NO_PROGRESS']
assert ns['call_mesh'](msgs)=='FAIL'
print('CONTRACT_DYNAMIC_PASS')
