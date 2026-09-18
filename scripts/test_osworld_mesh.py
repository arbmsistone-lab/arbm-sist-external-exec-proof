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
  return {'ok':True,'status':'PASS','pipeline':shim.EXPECTED_PIPELINE,'agent_build':shim.EXPECTED_BUILD,'mandatory_cost_usd':0,'paid_fallback_used':False,'provider':'groq-free','model':'free-model','provider_attempts':[{'route':'groq-multimodal-free','model':'free-model','status':200,'free_plan_proven':True}],'action':action or {'action':'exec','command':"pyautogui.press('enter')"},**overrides}
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

 def test_local_only_hint_cannot_capture_failover_mesh(self):
  body={'instruction':'edit the image','observation':'GIMP canvas','screenshot_data_url':'data:image/png;base64,AA==','provider_hint':'local-only'}
  remote_result={'provider':'openrouter-free','model':'or-free','action':{'action':'exec','command':"pyautogui.press('enter')"}}
  with patch.object(shim.FREE_ROUTE,'call',return_value=(remote_result,[{'route':'openrouter-multimodal-free','model':'or-free','status':200,'free_plan_proven':True}])) as router, \
       patch.object(shim.GROQ_FREE_ROUTE,'call',side_effect=AssertionError('groq should not run after earlier success')), \
       patch.object(shim.LOCAL_VLM_ROUTE,'call',side_effect=AssertionError('local should not capture route')), \
       patch.object(shim,'request_gateway',side_effect=AssertionError('gateway should not run after earlier success')):
   http,data=shim.request_mesh(body)
  self.assertEqual(http,200);self.assertTrue(router.called)
  self.assertEqual(data['provider'],'openrouter-free')

 def test_openrouter_first_prevents_unnecessary_groq_dependency(self):
  body={'instruction':'edit','observation':'GIMP','screenshot_data_url':'data:image/png;base64,AA=='}
  remote_result={'provider':'openrouter-free','model':'or-free','action':{'action':'exec','command':"pyautogui.press('enter')"}}
  with patch.object(shim.FREE_ROUTE,'call',return_value=(remote_result,[{'route':'openrouter-multimodal-free','model':'or-free','status':200,'free_plan_proven':True}])) as router, \
       patch.object(shim.GROQ_FREE_ROUTE,'call',side_effect=AssertionError('groq must not run after OpenRouter success')):
   http,data=shim.request_mesh(body)
  self.assertEqual(http,200);self.assertTrue(router.called);self.assertEqual(data['provider'],'openrouter-free')
 def test_full_free_mesh_exhaustion_is_fail_closed_not_wait_loop(self):
  shim.request_mesh=lambda b:(503,{'status':'FREE_MESH_EXHAUSTED_CURRENT_CYCLE','provider_attempts':[]})
  result=shim.call_mesh(self.msgs)
  self.assertEqual(result,'FAIL')
  self.assertEqual(shim.STATE['terminal'],'PROVIDER_CAPACITY_EXHAUSTED')
  self.assertEqual(shim.VERIFIER.no_progress,0)

 def test_capacity_retry_stays_inside_same_osworld_turn(self):
  calls=[]
  def unavailable(body):
   calls.append(dict(body));return 503,{'status':'NO_ZERO_SPEND_MULTIMODAL_CAPACITY','provider_attempts':[]}
  shim.request_mesh=unavailable
  result=shim.call_mesh(self.msgs)
  self.assertEqual(result,'FAIL')
  self.assertEqual(len(calls),3)
  self.assertEqual(calls[1].get('provider_hint'),'openrouter')
  self.assertEqual(calls[2].get('provider_hint'),'text')
  self.assertEqual(shim.STATE['terminal'],'PROVIDER_CAPACITY_EXHAUSTED')

 def test_visual_capacity_failure_never_sets_sticky_local_only(self):
  bodies=[]
  self.msgs=[{'role':'system','content':'You are asked to complete the following task: apply the same color grading in GIMP'},
             {'role':'user','content':'menu\tGNU Image Manipulation Program\t""\t\t\t(99, 0)\t(287, 27)'}]
  def unavailable(body):
   bodies.append(dict(body));return 503,{'status':'NO_ZERO_SPEND_MULTIMODAL_CAPACITY'}
  shim.request_mesh=unavailable
  self.assertEqual(shim.call_mesh(self.msgs),'FAIL')
  self.assertTrue(all(x.get('provider_hint')!='local-only' for x in bodies))
  self.assertEqual([x.get('provider_hint') for x in bodies],[None,'openrouter','text'])
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
  second=self.response({'action':'exec','command':'pyautogui.click(344, 64)','plan':'open Colors for a visible target adjustment','target':{'source':'accessibility','label':'Colors','role':'menu'}})
  responses=[(200,first),(200,second)]
  def mesh(body):
   bodies.append(dict(body));return responses.pop(0)
  shim.request_mesh=mesh
  self.assertIn('pyautogui.click(344, 64)',shim.call_mesh(self.msgs))
  self.assertEqual(len(bodies),2)
  self.assertIn('VISUAL-REFERENCE RECOVERY',bodies[0]['recovery_strategy'])
  self.assertIn('Ctrl+L',bodies[0]['recovery_strategy'])
  self.assertIsNone(bodies[1].get('provider_hint'))

 def test_task091_spatial_specialist_uses_live_atspi_targets_and_bounded_modal_clear(self):
  task=('You are Maya Lin, Business Operations Manager at Northstar Cloud. '
        'The COO has asked you to rebaseline the H2 Operating Committee pack. '
        'The draft deck Operating_Committee_Rebaseline_Draft.pptx is open. '
        'Reforecast_Model_H2.xlsx is the source of truth.')
  transient={'schema':1,'stable':True,'window':{
   'id':50331694,'pid':2689,'title':'System Check',
   'owner_title':'Operating_Committee_Rebaseline_Draft.pptx - WPS Office',
   'wm_class':'wpp wpp','bbox':[120,112,699,327]}}
  deck={'schema':1,'stable':True,'window':{
   'id':50331680,'pid':2689,'title':'Operating_Committee_Rebaseline_Draft.pptx - WPS Office',
   'owner_title':'','wm_class':'wpp wpp','bbox':[70,27,1850,1053]}}
  deck_obs=('text\tOperating Committee\tOperating Committee\t\t\t(500, 180)\t(600, 60)\n'
            'text\tGrowth Plan Draft\tGrowth Plan Draft\t\t\t(700, 300)\t(100, 40)')
  with patch.dict(os.environ,{'TASK_ID':'091','ZERO_SPEND_MODE':'HARD'},clear=False):
   state={}
   tab=shim.next_091_specialist_action(task,'WPS 2019','',state,transient)
   space=shim.next_091_specialist_action(task,'WPS 2019','',state,transient)
   self.assertEqual(tab['command'],"pyautogui.press('tab')")
   self.assertEqual(space['command'],"pyautogui.press('space')")
   self.assertNotIn("alt', 'tab",tab['command']+space['command'])
   self.assertNotIn("alt', 'f4",tab['command']+space['command'])
   self.assertFalse(state.get('anchored'))

   # If Space closes the modal, ownership transitions directly to the deck.
   anchor=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,deck)
   self.assertEqual(anchor['command'],"pyautogui.hotkey('ctrl', 'home')")
   self.assertEqual(state.get('mode'),'DECK_ACTIVE')

   # If Space does not close, only one guest-proven Close control may be clicked.
   fallback_state={}
   self.assertEqual(shim.next_091_specialist_action(task,'WPS 2019','',fallback_state,transient)['command'],
                    "pyautogui.press('tab')")
   self.assertEqual(shim.next_091_specialist_action(task,'WPS 2019','',fallback_state,transient)['command'],
                    "pyautogui.press('space')")
   transient_close={**transient,'controls':[{
      'label':'Close','role':'push button','pid':2689,'application':'wps',
      'bbox':[650,360,90,32],'showing':True,'enabled':True,'focused':True}]}
   click=shim.next_091_specialist_action(task,'WPS 2019','',fallback_state,transient_close)
   self.assertEqual(click['command'],'pyautogui.click(695, 376)')
   self.assertEqual(click['target']['source'],'accessibility')
   self.assertEqual(click['target']['label'],'Close')
   fallback_anchor=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,fallback_state,deck)
   self.assertEqual(fallback_anchor['command'],"pyautogui.hotkey('ctrl', 'home')")

   missing_close={}
   shim.next_091_specialist_action(task,'WPS 2019','',missing_close,transient)
   shim.next_091_specialist_action(task,'WPS 2019','',missing_close,transient)
   missing_terminal=shim.next_091_specialist_action(task,'WPS 2019','',missing_close,transient)
   self.assertEqual(missing_terminal['reason'],'TASK091_TARGET_NOT_VISIBLE')

   ambiguous_close={}
   shim.next_091_specialist_action(task,'WPS 2019','',ambiguous_close,transient)
   shim.next_091_specialist_action(task,'WPS 2019','',ambiguous_close,transient)
   two={**transient,'controls':[
      {'label':'Close','role':'push button','pid':2689,'application':'wps',
       'bbox':[650,360,90,32],'showing':True,'enabled':True,'focused':True},
      {'label':'Close','role':'push button','pid':2689,'application':'wps',
       'bbox':[500,360,90,32],'showing':True,'enabled':True,'focused':False}]}
   ambiguous_terminal=shim.next_091_specialist_action(task,'WPS 2019','',ambiguous_close,two)
   self.assertEqual(ambiguous_terminal['reason'],'TASK091_TARGET_AMBIGUOUS')

   required={'$40.9M','$2.8M','104%','71%','17 mo','206','3',
             'Renewal saves','Pricing discipline','Migration delay','Support credits',
             'International Pilot stop','Partner stabilization','Platform','Reliability',
             'Protected hiring','Freeze','Vendor SLA breach','Data migration cutover failure',
             'Reliability Hardening','Data Migration','H2 Stabilize-and-Recover Roadmap',
             'Protect Reliability Hardening capacity','Sequence Data Migration cutover',
             'Freeze non-critical hiring','Incident runbook rollout','Cutover rehearsal complete',
             'Recovery review with OpCom'}
   finals={row[4] for row in shim.TASK091_SPATIAL_TEXT_EDITS}
   self.assertTrue(required.issubset(finals))
   self.assertIn((2,558,364,'$42.8M','$40.9M'),shim.TASK091_SPATIAL_TEXT_EDITS)
   self.assertIn((3,843,404,'$42.8M','$40.9M'),shim.TASK091_SPATIAL_TEXT_EDITS)

   # First edit is a two-phase transaction and index cannot advance early.
   select=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,deck)
   self.assertEqual(select['target']['source'],'accessibility')
   self.assertIn('doubleClick(750, 320',select['command'])
   self.assertEqual(state['spatial_index'],0)
   self.assertEqual(state['pending_edit']['stage'],'select-issued')

   edit=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,deck)
   self.assertIn("hotkey('ctrl', 'a')",edit['command'])
   self.assertEqual(state['spatial_index'],0)
   self.assertEqual(state['pending_edit']['stage'],'edit-issued')

   commit_obs=('text\tOperating Committee\tOperating Committee\t\t\t(500, 180)\t(600, 60)\n'
               'text\tH2 Operating Committee Pack Stabilize-and-Recover Rebaseline\t'
               'H2 Operating Committee Pack Stabilize-and-Recover Rebaseline\t\t\t(700, 300)\t(220, 40)')
   commit=shim.next_091_specialist_action(task,'WPS Presentation',commit_obs,state,deck)
   self.assertEqual(commit['command'],"pyautogui.press('esc')")
   self.assertEqual(state['spatial_index'],0)
   self.assertEqual(state['pending_edit']['stage'],'commit-issued')
   verified=shim.next_091_specialist_action(task,'WPS Presentation',commit_obs,state,deck)
   self.assertEqual(verified['action'],'checkpoint')
   self.assertEqual(verified['checkpoint'],'TASK091_FIRST_STRUCTURAL_EDIT_VERIFIED')
   self.assertEqual(state['spatial_index'],1)
   self.assertIsNone(state.get('pending_edit'))
   self.assertTrue(state.get('first_structural_edit_verified'))

   # No semantic old->new change remains pending, then terminates specifically.
   stuck={'owned':True,'anchored':True,'slide':1,'spatial_index':0,'mode':'TARGET_COMMITTED',
          'pending_edit':{'slide':1,'old':'Growth Plan Draft',
                          'new':'H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline',
                          'stage':'commit-issued','target':{'bbox':[700,300,100,40],'cx':750,'cy':320},
                          'verify_attempts':0}}
   retry=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,stuck,deck)
   self.assertIn('sleep',retry['command'])
   failed=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,stuck,deck)
   self.assertEqual(failed['action'],'terminal')
   self.assertEqual(failed['reason'],'TASK091_EDIT_NOT_VERIFIED')
   self.assertEqual(stuck['spatial_index'],0)

   # Missing and ambiguous targets never click blindly.
   missing_obs='text\tOperating Committee\tOperating Committee\t\t\t(500, 180)\t(600, 60)'
   missing={'owned':True,'anchored':True,'slide':1,'spatial_index':0}
   self.assertIn('sleep',shim.next_091_specialist_action(task,'WPS Presentation',missing_obs,missing,deck)['command'])
   miss_terminal=shim.next_091_specialist_action(task,'WPS Presentation',missing_obs,missing,deck)
   self.assertEqual(miss_terminal['reason'],'TASK091_TARGET_NOT_VISIBLE')
   dup=('text\tOperating Committee\tOperating Committee\t\t\t(500, 180)\t(600, 60)\n'
        'text\tGrowth Plan Draft\tGrowth Plan Draft\t\t\t(690, 300)\t(100, 40)\n'
        'text\tGrowth Plan Draft\tGrowth Plan Draft\t\t\t(700, 300)\t(100, 40)')
   ambiguous={'owned':True,'anchored':True,'slide':1,'spatial_index':0}
   self.assertIn('sleep',shim.next_091_specialist_action(task,'WPS Presentation',dup,ambiguous,deck)['command'])
   amb_terminal=shim.next_091_specialist_action(task,'WPS Presentation',dup,ambiguous,deck)
   self.assertEqual(amb_terminal['reason'],'TASK091_TARGET_AMBIGUOUS')

   # A normal deck never receives transient close keys.
   normal={}
   normal_action=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,normal,deck)
   self.assertNotIn("press('enter')",normal_action['command'])
   self.assertNotIn("alt', 'f4",normal_action['command'])

   # Handoff is explicit, only after no pending edit and verified text pass saved.
   done={'owned':True,'anchored':True,'slide':13,'spatial_index':len(shim.TASK091_SPATIAL_TEXT_EDITS)}
   save=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,done,deck)
   self.assertIn("hotkey('ctrl', 's')",save['command'])
   self.assertIsNone(shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,done,deck))
   self.assertTrue(done.get('handoff'))
   self.assertEqual(done.get('handoff_reason'),'DIRECT_TEXT_PASS_VERIFIED_CHART_FILL_REMAINS')

 def test_task091_specialist_does_not_capture_other_tasks(self):
  with patch.dict(os.environ,{'TASK_ID':'061'},clear=False):
   self.assertIsNone(shim.next_091_specialist_action(
    'rebaseline H2 Operating Committee pack using Reforecast_Model_H2.xlsx',
    'WPS Presentation','',{}))

if __name__=='__main__':unittest.main()
