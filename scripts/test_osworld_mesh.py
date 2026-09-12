import sys,unittest,tempfile,pathlib,importlib.util,copy,json
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import osworld_free_mesh_shim as shim
from osworld_control import Verifier

class MeshTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  shim.LOG=str(pathlib.Path(self.tmp.name)/'log.jsonl');shim.OBS_DIR=pathlib.Path(self.tmp.name)/'obs'
  shim.STATE={'step':0,'previous':'','executed':0,'phase':'plan','plan':'','memory':[],'history':[],'wait_responses':0,'cooldowns':{},'terminal':'','provider':'','model':''}
  shim.VERIFIER=Verifier();shim.time.sleep=lambda *_:None
  self.msgs=[{'role':'system','content':'You are asked to complete the following task: press enter'},{'role':'user','content':'saved output button'}]
 def response(self,action=None,**overrides):
  return {'ok':True,'status':'PASS','pipeline':shim.EXPECTED_PIPELINE,'agent_build':shim.EXPECTED_BUILD,'mandatory_cost_usd':0,'paid_fallback_used':False,'provider':'mistral-free','model':'free-model','provider_attempts':[{'route':'mistral-multimodal-free','model':'free-model','status':200,'zero_spend_confirmed':True}],'action':action or {'action':'exec','command':"pyautogui.press('enter')"},**overrides}
 def test_error_recovery(self):
  for status in (413,422,429,500,502,503,504):
   with self.subTest(status=status):
    self.setUp();seq=[(status,{'status':'TRANSIENT'}),(200,self.response())]
    shim.request_mesh=lambda body:seq.pop(0)
    self.assertIn('pyautogui.press',shim.call_mesh(self.msgs))
 def test_endpoint_mismatch_terminal(self):
  shim.request_mesh=lambda b:(200,self.response(agent_build='changed'))
  self.assertEqual(shim.call_mesh(self.msgs),'FAIL')
  self.assertEqual(shim.STATE['terminal'],'ENDPOINT_INCOMPATIBLE')
 def test_cost_proof_terminal(self):
  shim.request_mesh=lambda b:(200,self.response(paid_fallback_used=True))
  self.assertEqual(shim.call_mesh(self.msgs),'FAIL')
 def test_rejected_command_is_never_issued(self):
  seq=[(200,self.response({'action':'exec','command':'pyautogui.click(1,2),[object Object]'})),(200,self.response())]
  shim.request_mesh=lambda b:seq.pop(0)
  self.assertIn('pyautogui.press',shim.call_mesh(self.msgs))
 def test_finish_premature_then_valid_action(self):
  seq=[(200,self.response({'action':'finish','confidence':1,'verification':'saved output'})),(200,self.response())]
  shim.request_mesh=lambda b:seq.pop(0)
  self.assertIn('pyautogui.press',shim.call_mesh(self.msgs))
 def test_quota_cooldown_persists(self):
  shim.track_attempts({'provider_attempts':[{'route':'r','model':'m','status':413}]})
  self.assertGreater(shim.STATE['cooldowns']['r:m'],shim.time.time()*1000+3_000_000)
 def test_provider_wait_does_not_masquerade_as_cognitive_failure(self):
  shim.request_mesh=lambda b:(503,self.response(ok=False,status='NO_ZERO_SPEND_MULTIMODAL_CAPACITY'))
  results=[shim.call_mesh(self.msgs) for _ in range(15)]
  self.assertEqual(set(results),{'WAIT'})
  self.assertEqual(shim.VERIFIER.no_progress,0)
  self.assertEqual(shim.STATE['terminal'],'')
 def test_provider_wait_has_independent_terminal_budget(self):
  shim.request_mesh=lambda b:(503,self.response(ok=False,status='NO_ZERO_SPEND_MULTIMODAL_CAPACITY'))
  shim.MAX_WAIT_RESPONSES=3
  results=[shim.call_mesh(self.msgs) for _ in range(5)]
  self.assertIn('WAIT',results);self.assertIn('FAIL',results)
  self.assertEqual(shim.STATE['terminal'],'RECOVERY_EXHAUSTED')
 def test_native_openai_error_code(self):
  import threading,urllib.request,urllib.error
  server=shim.ThreadingHTTPServer(('127.0.0.1',0),shim.Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   req=urllib.request.Request('http://127.0.0.1:%s/v1/chat/completions'%server.server_port,data=b'{bad',headers={'Content-Type':'application/json'})
   with self.assertRaises(urllib.error.HTTPError) as c:urllib.request.urlopen(req)
   data=json.loads(c.exception.read());self.assertEqual(data['error']['code'],'shim_internal_error')
  finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()
