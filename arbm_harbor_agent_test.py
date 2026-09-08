import importlib.util, json, os, sys, threading, unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

# Stub Harbor modules so the policy layer can be tested without installing Harbor.
class BaseAgent: pass
class BaseEnvironment: pass
class AgentContext: pass
mods={
 'harbor.agents.base':('BaseAgent',BaseAgent),
 'harbor.environments.base':('BaseEnvironment',BaseEnvironment),
 'harbor.models.agent.context':('AgentContext',AgentContext)}
import types
for name,(attr,val) in mods.items():
 m=types.ModuleType(name); setattr(m,attr,val); sys.modules[name]=m

spec=importlib.util.spec_from_file_location('agent','arbm_harbor_agent.py')
agent=importlib.util.module_from_spec(spec); spec.loader.exec_module(agent)

class Handler(BaseHTTPRequestHandler):
 def log_message(self,*a): pass
 def do_POST(self):
  body=json.dumps({'choices':[{'message':{'content':'{"action":"exec","command":"pwd","summary":"inspect"}'}}]}).encode()
  self.send_response(200); self.send_header('content-type','application/json'); self.send_header('content-length',str(len(body))); self.end_headers(); self.wfile.write(body)

class Tests(unittest.TestCase):
 def test_sovereign_contract_is_zero_cost(self):
  srv=ThreadingHTTPServer(('127.0.0.1',0),Handler); threading.Thread(target=srv.serve_forever,daemon=True).start()
  old=agent.SOVEREIGN_URL; agent.SOVEREIGN_URL=f'http://127.0.0.1:{srv.server_port}/v1/chat/completions'
  try:
   out=agent.ARBMHarborAgent()._sovereign_decide('inspect','none',1)
   self.assertEqual(out['action']['command'],'pwd'); self.assertEqual(out['mandatory_cost_usd'],0); self.assertFalse(out['paid_fallback_used']); self.assertEqual(out['provider'],'sovereign-qwen-github')
  finally: agent.SOVEREIGN_URL=old; srv.shutdown(); srv.server_close()
 def test_remote_failure_uses_sovereign_only_when_enabled(self):
  a=agent.ARBMHarborAgent()
  with patch.object(a,'_oidc',return_value='token'), patch.object(agent.urllib.request,'urlopen',side_effect=agent.urllib.error.URLError('offline')), patch.object(a,'_sovereign_decide',return_value={'ok':True,'action':{'action':'finish','summary':'ok'},'mandatory_cost_usd':0,'paid_fallback_used':False}) as sovereign, patch.object(agent.time,'sleep'):
   with patch.dict(os.environ,{'ARBM_ENABLE_SOVEREIGN_FALLBACK':'1'}): self.assertTrue(a._decide('x','y',1)['ok'])
   sovereign.assert_called_once()

if __name__=='__main__': unittest.main()
