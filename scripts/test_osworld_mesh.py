import sys,unittest,tempfile,pathlib,importlib.util,copy,json
import os
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import osworld_free_mesh_shim as shim
REAL_REQUEST_MESH=shim.request_mesh
from osworld_control import Verifier

class MeshTests(unittest.TestCase):
 def setUp(self):
  shim.request_mesh=REAL_REQUEST_MESH
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  shim.LOG=str(pathlib.Path(self.tmp.name)/'log.jsonl');shim.OBS_DIR=pathlib.Path(self.tmp.name)/'obs'
  shim.STATE={'step':0,'previous':'','executed':0,'phase':'plan','plan':'','memory':[],'history':[],'wait_responses':0,'cooldowns':{},'terminal':'','provider':'','model':''}
  shim.VERIFIER=Verifier();shim.MILESTONES=shim.Milestones();shim.MAX_WAIT_RESPONSES=60
  self.sleeper=patch.object(shim.time,'sleep',lambda *_:None);self.sleeper.start();self.addCleanup(self.sleeper.stop)
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
 def test_transient_remote_capacity_falls_back_to_local_action_vlm(self):
  body={'instruction':'edit the image','observation':'GIMP canvas','screenshot_data_url':'data:image/png;base64,AA=='}
  remote={'status':'NO_ZERO_SPEND_MULTIMODAL_CAPACITY','provider_attempts':[]}
  local_result={'provider':'local-cloud-vlm','model':'local-test','action':{'action':'exec','command':"pyautogui.press('enter')"}}
  with patch.object(shim.GROQ_FREE_ROUTE,'call',return_value=(None,[{'route':'groq','model':'m','status':429}])),        patch.object(shim,'request_gateway',return_value=(503,remote)),        patch.object(shim.FREE_ROUTE,'call',return_value=(None,[{'route':'openrouter','model':'m','status':429}])),        patch.object(shim.LOCAL_VLM_ROUTE,'call',return_value=(local_result,[{'route':'local-cloud-vlm','model':'local-test','status':200,'zero_spend_confirmed':True}])):
   http,data=shim.request_mesh(body)
  self.assertEqual(http,200)
  self.assertEqual(data['provider'],'local-cloud-vlm')
  self.assertEqual(data['mandatory_cost_usd'],0)
  self.assertFalse(data['paid_fallback_used'])
  self.assertEqual(data['action']['command'],"pyautogui.press('enter')")

 def test_semantic_capacity_response_falls_back_to_local_action_vlm(self):
  body={'instruction':'edit the image','observation':'GIMP canvas','screenshot_data_url':'data:image/png;base64,AA=='}
  remote={'status':'NO_ZERO_SPEND_MULTIMODAL_CAPACITY','provider_attempts':[]}
  local_result={'provider':'local-cloud-vlm','model':'local-test','action':{'action':'exec','command':"pyautogui.press('enter')"}}
  with patch.object(shim.GROQ_FREE_ROUTE,'call',return_value=(None,[{'route':'groq','model':'m','status':429}])),        patch.object(shim,'request_gateway',return_value=(200,remote)),        patch.object(shim.FREE_ROUTE,'call',return_value=(None,[{'route':'openrouter','model':'m','status':429}])),        patch.object(shim.LOCAL_VLM_ROUTE,'call',return_value=(local_result,[{'route':'local-cloud-vlm','model':'local-test','status':200,'zero_spend_confirmed':True}])) as local:
   http,data=shim.request_mesh(body)
  self.assertTrue(local.called)
  self.assertEqual(http,200)
  self.assertEqual(data['provider'],'local-cloud-vlm')
  self.assertEqual(data['mandatory_cost_usd'],0)
  self.assertFalse(data['paid_fallback_used'])

 def test_local_only_never_probes_remote_providers(self):
  body={'instruction':'edit the image','observation':'GIMP canvas','screenshot_data_url':'data:image/png;base64,AA==','provider_hint':'local-only'}
  local_result={'provider':'local-cloud-vlm','model':'local-test','action':{'action':'exec','command':"pyautogui.press('enter')"}}
  with patch.object(shim.GROQ_FREE_ROUTE,'call',side_effect=AssertionError('groq must not run')),        patch.object(shim,'request_gateway',side_effect=AssertionError('gateway must not run')),        patch.object(shim.FREE_ROUTE,'call',side_effect=AssertionError('openrouter must not run')),        patch.object(shim.LOCAL_VLM_ROUTE,'call',return_value=(local_result,[{'route':'local-cloud-vlm','model':'local-test','status':200,'zero_spend_confirmed':True}])):
   http,data=shim.request_mesh(body)
  self.assertEqual(http,200)
  self.assertEqual(data['provider'],'local-cloud-vlm')

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
 def test_visual_provider_outage_degrades_to_accessibility_before_terminal(self):
  bodies=[]
  self.msgs=[{'role':'system','content':'You are asked to complete the following task: apply the same color grading in GIMP'},
             {'role':'user','content':'menu\tGNU Image Manipulation Program\t""\t\t\t(99, 0)\t(287, 27)'}]
  def unavailable(body):
   bodies.append(dict(body))
   return 503,{'status':'NO_ZERO_SPEND_MULTIMODAL_CAPACITY'}
  shim.request_mesh=unavailable
  # This case proves the accessibility-only degradation when the local VLM is
  # unavailable.  CI normally enables it, so make that prerequisite explicit.
  with patch.dict(os.environ,{'ARBM_ENABLE_LOCAL_VLM':'0'}):
   for _ in range(4):self.assertEqual(shim.call_mesh(self.msgs),'WAIT')
  self.assertTrue(shim.STATE['visual_capacity_exhausted'])
  self.assertEqual(bodies[-1]['provider_hint'],'text')
 def test_corrupt_http_input_terminates_without_client_retry(self):
  import threading,urllib.request,urllib.error
  server=shim.ThreadingHTTPServer(('127.0.0.1',0),shim.Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   req=urllib.request.Request('http://127.0.0.1:%s/v1/chat/completions'%server.server_port,data=b'{bad',headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req) as res:
    self.assertEqual(res.status,200);data=json.loads(res.read())
   self.assertEqual(data['choices'][0]['message']['content'],'FAIL')
   self.assertTrue(shim.STATE['terminal'].startswith('INPUT_REJECTED:'))
  finally:server.shutdown();server.server_close();thread.join()
 def test_http_run38_sized_history_reaches_mesh_once(self):
  import threading,urllib.request
  calls=[]
  def mesh(messages):calls.append(messages);return 'WAIT'
  server=shim.ThreadingHTTPServer(('127.0.0.1',0),shim.Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   raw=json.dumps({'messages':[{'role':'system','content':'task'}]+[{'role':'user','content':'x'*1_700_000} for _ in range(20)]}).encode()
   req=urllib.request.Request('http://127.0.0.1:%s/v1/chat/completions'%server.server_port,data=raw,headers={'Content-Type':'application/json'})
   with patch.object(shim,'call_mesh',mesh),urllib.request.urlopen(req,timeout=20) as res:
    self.assertEqual(res.status,200);self.assertEqual(json.loads(res.read())['choices'][0]['message']['content'],'WAIT')
   self.assertEqual(len(calls),1);self.assertEqual(len(calls[0]),2)
  finally:server.shutdown();server.server_close();thread.join()
 def test_future_claims_do_not_poison_durable_memory(self):
  shim.request_mesh=lambda b:(200,self.response({'action':'exec','command':"pyautogui.press('enter')",'memory_patch':'All appointments created and saved'}))
  shim.call_mesh(self.msgs)
  self.assertEqual(shim.STATE['memory'],[])
 def test_deadline_preserves_time_for_evaluator(self):
  with patch.object(shim,'STARTED',shim.time.monotonic()-shim.MAX_TASK_SECONDS):
   self.assertEqual(shim.call_mesh(self.msgs),'FAIL')
  self.assertEqual(shim.STATE['terminal'],'TASK_DEADLINE')
 def test_task061_artifact_replay_rejects_repeated_open_before_vm_action(self):
  # Minimal foreground evidence taken from focal run 34758386722, step 16:
  # GIMP was active, the target was selected, and Ctrl+O had already been used.
  task=('Apply the same style and color grading from reference.jpg to target.jpg in GIMP. '
        'Save target_edited.jpg in Pictures.')
  observation=('menu\tGNU Image Manipulation Program\t""\t\t\t(99, 0)\t(287, 27)\n'
               'menu\tColors\tColors\t\t\t(344, 64)\t(56, 25)\n'
               'table-cell\ttarget.jpg\ttarget.jpg\t\t\t(1846, 555)\t(136, 38)')
  self.msgs=[{'role':'system','content':'You are asked to complete the following task: '+task},
             {'role':'user','content':observation}]
  shim.MILESTONES.stalled=8
  bodies=[]
  first=self.response({'action':'exec','command':"pyautogui.hotkey('ctrl', 'o')",'plan':'open the target again'})
  second=self.response({'action':'exec','command':'pyautogui.click(344, 64)','plan':'open Colors for a visible target adjustment'})
  responses=[(200,first),(200,second)]
  def mesh(body):
   bodies.append(dict(body));return responses.pop(0)
  shim.request_mesh=mesh
  self.assertIn('pyautogui.click(344, 64)',shim.call_mesh(self.msgs))
  self.assertEqual(len(bodies),2)
  self.assertIn('VISUAL-REFERENCE RECOVERY',bodies[0]['recovery_strategy'])
  self.assertIn('Ctrl+L',bodies[0]['recovery_strategy'])
  self.assertIsNone(bodies[1].get('provider_hint'))
if __name__=='__main__':unittest.main()
