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
  import http.client,threading
  server=shim.ThreadingHTTPServer(('127.0.0.1',0),shim.Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  connection=None
  try:
   connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10)
   connection.request('POST','/v1/chat/completions',body=b'{bad',headers={'Content-Type':'application/json'})
   res=connection.getresponse()
   self.assertEqual(res.status,200);data=json.loads(res.read())
   self.assertEqual(data['choices'][0]['message']['content'],'FAIL')
   self.assertTrue(shim.STATE['terminal'].startswith('INPUT_REJECTED:'))
  finally:
   if connection is not None: connection.close()
   server.shutdown();server.server_close();thread.join()
 def test_http_run38_sized_history_reaches_mesh_once(self):
  import http.client,threading
  calls=[]
  def mesh(messages):calls.append(messages);return 'WAIT'
  server=shim.ThreadingHTTPServer(('127.0.0.1',0),shim.Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  connection=None
  try:
   raw=json.dumps({'messages':[{'role':'system','content':'task'}]+[{'role':'user','content':'x'*1_700_000} for _ in range(20)]}).encode()
   connection=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=20)
   with patch.object(shim,'call_mesh',mesh):
    connection.request('POST','/v1/chat/completions',body=raw,headers={'Content-Type':'application/json'})
    res=connection.getresponse()
    self.assertEqual(res.status,200);self.assertEqual(json.loads(res.read())['choices'][0]['message']['content'],'WAIT')
   self.assertEqual(len(calls),1);self.assertEqual(len(calls[0]),2)
  finally:
   if connection is not None: connection.close()
   server.shutdown();server.server_close();thread.join()
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
   'owner_title':'','wm_class':'wpp wpp','bbox':[70,27,1850,1053]},
   'screen':[0,0,1920,1080],
   'active_slide':1,
   'screenshot_sha256':'1'*64,
   'deck_slide_text':{'1':'Growth Plan Draft Planning posture: accelerate growth through H2 scale-up $42.8M $2.6M 214'},
   'deck_slide_runs':{'1':['Growth Plan Draft','Planning posture: accelerate growth through H2 scale-up','$42.8M','$2.6M','214']},
   'deck_slide_shapes':{'1':[
      {'id':6,'name':'CoverTitle','text':'H2 Operating Committee Pack\nGrowth Plan Draft',
       'paragraphs':['H2 Operating Committee Pack','Growth Plan Draft'],
       'geometry':{'x':749808,'y':1078992,'w':5852160,'h':1234440}},
      {'id':7,'name':'CoverSub','text':'Northstar Cloud\nPrepared for July Operating Committee review\nPlanning posture: accelerate growth through H2 scale-up',
       'paragraphs':['Northstar Cloud','Prepared for July Operating Committee review',
                     'Planning posture: accelerate growth through H2 scale-up'],
       'geometry':{'x':768096,'y':2743200,'w':5669280,'h':1280160}}]},
   'deck_file':{'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                'sha256':'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                'size':1234,'mtime_ns':1,'slide_size':{'w':12192000,'h':6858000}}}
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
   self.assertEqual(select['target']['source'],'task091-pptx-canonical')
   self.assertEqual(select['command'],'pyautogui.doubleClick(745, 335, interval=0.08)')
   self.assertEqual(state['pending_edit']['shape_id'],6)
   self.assertEqual(state['spatial_index'],0)
   self.assertEqual(state['pending_edit']['stage'],'select-issued')

   selected=copy.deepcopy(deck)
   selected['screenshot_sha256']='2'*64
   edit=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,selected)
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
   save_pending=shim.next_091_specialist_action(task,'WPS Presentation',commit_obs,state,deck)
   self.assertIn("hotkey('ctrl', 's')",save_pending['command'])
   self.assertEqual(state['pending_edit']['stage'],'save-issued')
   deck_after={**deck,'deck_slide_text':{'1':'H2 Operating Committee Pack Stabilize-and-Recover Rebaseline Planning posture: accelerate growth through H2 scale-up $42.8M $2.6M 214'},
               'deck_slide_runs':{'1':['H2 Operating Committee Pack','Stabilize-and-Recover Rebaseline',
                                       'Planning posture: accelerate growth through H2 scale-up','$42.8M','$2.6M','214']},
               'deck_slide_shapes':{'1':[
                   {'id':6,'name':'CoverTitle','text':'H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline',
                    'paragraphs':['H2 Operating Committee Pack','Stabilize-and-Recover Rebaseline'],
                    'geometry':{'x':749808,'y':1078992,'w':5852160,'h':1234440}},
                   deck['deck_slide_shapes']['1'][1]]},
               'deck_file':{'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                            'sha256':'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                            'size':1240,'mtime_ns':2,'slide_size':{'w':12192000,'h':6858000}}}
   verified=shim.next_091_specialist_action(task,'WPS Presentation',commit_obs,state,deck_after)
   self.assertEqual(verified['action'],'checkpoint')
   self.assertEqual(verified['checkpoint'],'TASK091_FIRST_STRUCTURAL_EDIT_VERIFIED')
   self.assertEqual(state['spatial_index'],1)
   self.assertIsNone(state.get('pending_edit'))
   self.assertTrue(state.get('first_structural_edit_verified'))

   # Shape-bound targeting must move to CoverSub and never re-edit CoverTitle.
   second_select=shim.next_091_specialist_action(task,'WPS Presentation','',state,deck_after)
   self.assertEqual(second_select['command'],'pyautogui.doubleClick(738, 516, interval=0.08)')
   self.assertEqual(state['pending_edit']['shape_id'],7)
   wrong_shape_after={**deck_after,
      'deck_slide_text':{'1':'Northstar Cloud Prepared for July Operating Committee review Planning posture: stabilize and recover with disciplined sequencing Planning posture: accelerate growth through H2 scale-up'},
      'deck_slide_shapes':{'1':[
          {'id':6,'name':'CoverTitle',
           'text':'Northstar Cloud\nPrepared for July Operating Committee review\nPlanning posture: stabilize and recover with disciplined sequencing',
           'paragraphs':['Northstar Cloud','Prepared for July Operating Committee review',
                         'Planning posture: stabilize and recover with disciplined sequencing'],
           'geometry':{'x':749808,'y':1078992,'w':5852160,'h':1234440}},
          deck_after['deck_slide_shapes']['1'][1]]},
      'deck_file':{'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                   'sha256':'e'*64,'size':1300,'mtime_ns':3,
                   'slide_size':{'w':12192000,'h':6858000}}}
   state['pending_edit']['stage']='save-issued'
   wrong=shim.next_091_specialist_action(task,'WPS Presentation','',state,wrong_shape_after)
   self.assertNotEqual(wrong.get('checkpoint'),'TASK091_STRUCTURAL_EDIT_VERIFIED')
   self.assertEqual(state['spatial_index'],1)

   # No semantic old->new change remains pending, then terminates specifically.
   stuck={'owned':True,'anchored':True,'slide':1,'spatial_index':0,'mode':'TARGET_COMMITTED',
          'pending_edit':{'slide':1,'old':'Growth Plan Draft',
                          'new':'H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline',
                          'stage':'commit-issued','target':{'bbox':[700,300,100,40],'cx':750,'cy':320},
                          'before_old_count':1,'before_new_count':0,'verify_attempts':0}}
   persist=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,stuck,deck)
   self.assertIn("hotkey('ctrl', 's')",persist['command'])
   retry=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,stuck,deck)
   self.assertIn('sleep',retry['command'])
   failed=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,stuck,deck)
   self.assertEqual(failed['action'],'terminal')
   self.assertEqual(failed['reason'],'TASK091_EDIT_NOT_VERIFIED')
   self.assertEqual(stuck['spatial_index'],0)

   self.assertIn("hotkey('shift', 'enter')",edit['command'])
   self.assertIn("interval=0.02",edit['command'])
   self.assertNotIn("interval=0.001",edit['command'])
   self.assertNotIn("\\n', interval",edit['command'])

   # Run 35411705196 proved a saved but key-repeat-corrupted first edit.
   # Recovery is allowed exactly once and still requires exact PPTX verification.
   corrupt_state={'owned':True,'anchored':True,'slide':1,'spatial_index':0,'mode':'TARGET_VERIFYING',
                  'pending_edit':{'slide':1,'old':'Growth Plan Draft',
                                  'new':'H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline',
                                  'stage':'save-issued',
                                  'target':{'label':'Growth Plan Draft','role':'task091-canonical-point',
                                            'bbox':[744,334,2,2],'cx':745,'cy':335,
                                            'source':'task091-pptx-canonical','slide':1},
                                  'before_old_count':1,'before_new_count':0,
                                  'shape_id':7,
                                  'before_deck_sha256':'a'*64,
                                  'selected_screenshot_sha256':'1'*64,
                                  'edited_screenshot_sha256':'2'*64,
                                  'verify_attempts':0}}
   corrupt_text='H2 Operating Committee Pack\nSStabilize-and-Recover Rebaseline'
   corrupt_deck={**deck,
                 'deck_slide_text':{'1':corrupt_text.replace('\n',' ')},
                 'deck_slide_runs':{'1':['H2 Operating Committee Pack','SStabilize-and-Recover Rebaseline']},
                 'deck_slide_shapes':{'1':[{'id':7,'name':'Title 1','text':corrupt_text,
                                            'paragraphs':['H2 Operating Committee Pack',
                                                          'SStabilize-and-Recover Rebaseline'],
                                            'geometry':{'x':749808,'y':1078992,'w':5852160,'h':922020}}]},
                 'deck_file':{'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                              'sha256':'c'*64,'size':110431,'mtime_ns':3,
                              'slide_size':{'w':12192000,'h':6858000}},
                 'screenshot_sha256':'3'*64}
   repair_select=shim.next_091_specialist_action(task,'WPS Presentation','',corrupt_state,corrupt_deck)
   self.assertEqual(repair_select['command'],'pyautogui.doubleClick(745, 335, interval=0.08)')
   self.assertNotEqual(repair_select['command'],'pyautogui.doubleClick(869, 373, interval=0.08)')
   self.assertEqual(repair_select['target']['source'],'task091-pptx-canonical')
   self.assertEqual(corrupt_state['pending_edit']['repair_attempts'],1)
   self.assertEqual(corrupt_state['pending_edit']['repair_before_deck_sha256'],'c'*64)
   self.assertEqual(corrupt_state['pending_edit']['repair_shape_id'],7)
   self.assertEqual(corrupt_state['pending_edit']['repair_target_cx'],745)
   self.assertEqual(corrupt_state['pending_edit']['repair_target_cy'],335)
   self.assertEqual(corrupt_state['pending_edit']['repair_shape_geometry']['h'],922020)
   self.assertGreater(len(corrupt_state['pending_edit']['repair_plan']),0)
   self.assertTrue(all(row['op'] in ('delete','linebreak') for row in corrupt_state['pending_edit']['repair_plan']))

   repair_selected={**corrupt_deck,'screenshot_sha256':'4'*64}
   repair_edit=shim.next_091_specialist_action(task,'WPS Presentation','',corrupt_state,repair_selected)
   self.assertIn("hotkey('ctrl', 'a')",repair_edit['command'])
   self.assertIn("'delete'",repair_edit['command'])
   self.assertNotIn('pyautogui.write(',repair_edit['command'])
   repair_edited={**corrupt_deck,'screenshot_sha256':'5'*64}
   repair_commit=shim.next_091_specialist_action(task,'WPS Presentation','',corrupt_state,repair_edited)
   self.assertEqual(repair_commit['command'],"pyautogui.press('esc')")
   repair_save=shim.next_091_specialist_action(task,'WPS Presentation','',corrupt_state,repair_edited)
   self.assertIn("hotkey('ctrl', 's')",repair_save['command'])

   repaired_text='H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'
   repaired_deck={**deck,
                  'deck_slide_text':{'1':repaired_text.replace('\n',' ')},
                  'deck_slide_runs':{'1':['H2 Operating Committee Pack','Stabilize-and-Recover Rebaseline']},
                  'deck_slide_shapes':{'1':[{'id':7,'name':'Title 1','text':repaired_text,
                                             'paragraphs':['H2 Operating Committee Pack',
                                                           'Stabilize-and-Recover Rebaseline'],
                                             'geometry':{'x':749808,'y':1078992,'w':5852160,'h':922020}}]},
                  'deck_file':{'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                               'sha256':'d'*64,'size':110500,'mtime_ns':4,
                               'slide_size':{'w':12192000,'h':6858000}},
                  'screenshot_sha256':'6'*64}
   repaired=shim.next_091_specialist_action(task,'WPS Presentation','',corrupt_state,repaired_deck)
   self.assertEqual(repaired['action'],'checkpoint')
   self.assertEqual(repaired['checkpoint'],'TASK091_FIRST_STRUCTURAL_EDIT_VERIFIED')
   self.assertEqual(corrupt_state['spatial_index'],1)

   latest_corrupt='H2 Operating Committee Pack\nSStabilize-and-Recover Rebaseline'
   self.assertEqual(shim._task091_delete_only_plan(
       latest_corrupt,'H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'),[29])
   self.assertIsNone(shim._task091_delete_only_plan(
       'H2 Operating Committee Pack\nBroken Rebaseline',
       'H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'))
   ambiguous_shapes={**corrupt_deck,'deck_slide_shapes':{'1':[
       {'id':7,'name':'Title 1','text':corrupt_text,'paragraphs':[],'geometry':{}},
       {'id':8,'name':'Title 2','text':corrupt_text,'paragraphs':[],'geometry':{}}]}}
   ambiguous_repair_state={'owned':True,'anchored':True,'slide':1,'spatial_index':0,
                           'pending_edit':{'slide':1,'old':'Growth Plan Draft',
                                           'new':'H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline',
                                           'stage':'save-issued','repair_attempts':0,
                                           'target':{'label':'Growth Plan Draft',
                                                     'role':'task091-canonical-point',
                                                     'bbox':[744,334,2,2],'cx':745,'cy':335,
                                                     'source':'task091-pptx-canonical','slide':1},
                                           'before_old_count':1,'before_new_count':0,
                                           'before_deck_sha256':'a'*64,
                                           'selected_screenshot_sha256':'1'*64,
                                           'edited_screenshot_sha256':'2'*64,
                                           'verify_attempts':0}}
   ambiguous_repair=shim.next_091_specialist_action(
       task,'WPS Presentation','',ambiguous_repair_state,ambiguous_shapes)
   self.assertEqual(ambiguous_repair['action'],'terminal')
   self.assertEqual(ambiguous_repair['reason'],'TASK091_EDIT_TEXT_MISMATCH_UNPROVEN')

   corrupt_twice={'owned':True,'anchored':True,'slide':1,'spatial_index':0,
                  'pending_edit':{'slide':1,'old':'Growth Plan Draft',
                                  'new':'H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline',
                                  'stage':'save-issued','repair_attempts':1,
                                  'repair_before_deck_sha256':'b'*64,
                                  'target':{'bbox':[744,334,2,2],'cx':745,'cy':335},
                                  'before_old_count':1,'before_new_count':0,
                                  'before_deck_sha256':'a'*64,'verify_attempts':1}}
   terminal_corrupt=shim.next_091_specialist_action(task,'WPS Presentation','',corrupt_twice,corrupt_deck)
   self.assertEqual(terminal_corrupt['action'],'terminal')
   self.assertEqual(terminal_corrupt['reason'],'TASK091_EDIT_TEXT_CORRUPTED')

   # Official WPS runner may expose no canvas AT-SPI. In that case only the
   # canonical Task 091 point is usable, and only when target-PPTX text proves
   # the expected old value on the expected slide.
   spatial_state={'owned':True,'anchored':True,'slide':1,'spatial_index':0}
   spatial=shim.next_091_specialist_action(task,'WPS Presentation','',spatial_state,deck)
   self.assertEqual(spatial['target']['source'],'task091-pptx-canonical')
   self.assertEqual(spatial['command'],'pyautogui.doubleClick(745, 335, interval=0.08)')
   self.assertEqual(spatial_state['pending_edit']['shape_id'],6)
   self.assertEqual(spatial_state['pending_edit']['before_old_count'],1)
   self.assertEqual(spatial['target']['proof_sha256'],shim.task091_spatial_target_proof(spatial['target']))
   grounded=shim.ground_action(spatial,'WPS Presentation','',[],allow_canonical=True)
   self.assertEqual(grounded['command'],spatial['command'])
   self.assertIn('PPTX-backed canonical target',grounded.get('compiler_note',''))
   with self.assertRaisesRegex(ValueError,'CANONICAL_TARGET_UNTRUSTED'):
    shim.ground_action(spatial,'WPS Presentation','',[],allow_canonical=False)
   tampered=copy.deepcopy(spatial); tampered['target']['deck_sha256']='b'*64
   with self.assertRaisesRegex(ValueError,'TASK091_CANONICAL_TARGET_PROOF_INVALID'):
    shim.ground_action(tampered,'WPS Presentation','',[],allow_canonical=True)
   no_old={**deck,'deck_slide_text':{'1':'Already changed'},
           'deck_slide_shapes':{'1':[deck['deck_slide_shapes']['1'][1]]}}
   no_old_state={'owned':True,'anchored':True,'slide':1,'spatial_index':0}
   retry_no_old=shim.next_091_specialist_action(task,'WPS Presentation','',no_old_state,no_old)
   self.assertIn('sleep',retry_no_old['command'])
   no_old_terminal=shim.next_091_specialist_action(task,'WPS Presentation','',no_old_state,no_old)
   self.assertEqual(no_old_terminal['reason'],'TASK091_SHAPE_GEOMETRY_UNPROVEN')

   # Missing and ambiguous targets never click blindly.
   missing_obs='text\tOperating Committee\tOperating Committee\t\t\t(500, 180)\t(600, 60)'
   missing_deck={**deck,'deck_slide_text':{'1':'Already finalized content without draft marker'},
                 'deck_slide_runs':{'1':['Already finalized content without draft marker']},
                 'deck_slide_shapes':{'1':[deck['deck_slide_shapes']['1'][1]]}}
   missing={'owned':True,'anchored':True,'slide':1,'spatial_index':0}
   self.assertIn('sleep',shim.next_091_specialist_action(task,'WPS Presentation',missing_obs,missing,missing_deck)['command'])
   miss_terminal=shim.next_091_specialist_action(task,'WPS Presentation',missing_obs,missing,missing_deck)
   self.assertEqual(miss_terminal['reason'],'TASK091_SHAPE_GEOMETRY_UNPROVEN')

   # Duplicate PPTX shapes containing the same old text are fail-closed.
   dup_shape=copy.deepcopy(deck['deck_slide_shapes']['1'][0])
   dup_shape['id']=106
   ambiguous_deck={**deck,'deck_slide_shapes':{'1':deck['deck_slide_shapes']['1']+[dup_shape]}}
   ambiguous={'owned':True,'anchored':True,'slide':1,'spatial_index':0}
   amb_retry=shim.next_091_specialist_action(task,'WPS Presentation','',ambiguous,ambiguous_deck)
   self.assertIn('sleep',amb_retry['command'])
   amb_terminal=shim.next_091_specialist_action(task,'WPS Presentation','',ambiguous,ambiguous_deck)
   self.assertEqual(amb_terminal['action'],'terminal')
   self.assertEqual(amb_terminal['reason'],'TASK091_SHAPE_GEOMETRY_UNPROVEN')

   no_op_index=next(i for i,row in enumerate(shim.TASK091_SPATIAL_TEXT_EDITS)
                    if shim._task091_norm(row[3]) == shim._task091_norm(row[4]))
   no_op_row=shim.TASK091_SPATIAL_TEXT_EDITS[no_op_index]
   no_op_state={'owned':True,'anchored':True,'slide':no_op_row[0],'spatial_index':no_op_index}
   no_op=shim.next_091_specialist_action(task,'WPS Presentation','',no_op_state,deck)
   self.assertEqual(no_op['action'],'checkpoint')
   self.assertEqual(no_op['checkpoint'],'TASK091_TARGET_ALREADY_FINAL')
   self.assertEqual(no_op_state['spatial_index'],no_op_index+1)

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


 def test_task091_restricted_repair_and_50x10_review_board(self):
  from arbm091.review_board_50x10 import evaluate
  actual='H2 Operating Committee PPackSStabilize-and-Recover RRebaseline'
  expected='H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'
  plan=shim._task091_restricted_repair_plan(actual,expected)
  self.assertEqual(plan,[
      {'op':'delete','index':24,'char':'P'},
      {'op':'linebreak','index':27},
      {'op':'delete','index':29,'char':'S'},
      {'op':'delete','index':51,'char':'R'}])
  with self.assertRaisesRegex(ValueError,'TASK091_REPAIR_ATOMIC_OPERATION_REQUIRED'):
   shim._task091_restricted_repair_command(plan)
  first=plan[0]
  command=shim._task091_restricted_repair_command([first])
  self.assertNotIn('pyautogui.write(',command)
  self.assertIn("press('delete')",command)
  self.assertLessEqual(len(command.splitlines()),5)
  from osworld_control import canonical_action
  compiled=canonical_action({'action':'exec','command':command})
  self.assertEqual(compiled['command'],command)
  shape={'id':6,'name':'CoverTitle','text':actual}
  verdict=evaluate(actual,expected,plan,shape,'a'*64,'b'*64)
  self.assertEqual(verdict['status'],'PASS')
  self.assertEqual(verdict['senior_pass'],50)
  self.assertEqual(verdict['master_pass'],10)
  unsafe=[{'op':'insert','index':27,'char':'S'}]
  with self.assertRaises(RuntimeError):
   evaluate(actual,expected,unsafe,shape,'a'*64,'b'*64)

 def test_task091_atomic_repair_chunks_long_caret_navigation(self):
  for index in (43,51):
   command=shim._task091_restricted_repair_command([{'op':'delete','index':index,'char':'R'}])
   self.assertNotIn('presses=31',command)
   self.assertNotIn('presses=43',command)
   self.assertNotIn('presses=51',command)
   self.assertIn("presses=30",command)
   self.assertLessEqual(len(command.splitlines()),5)
   self.assertEqual(command.splitlines()[0], "pyautogui.hotkey('ctrl', 'a')")
   from osworld_control import canonical_action
   compiled=canonical_action({'action':'exec','command':command})
   self.assertEqual(compiled['command'],command)
   self.assertEqual(command.count("pyautogui.press('delete')"),1)

 def test_task091_atomic_repair_replans_from_persisted_text(self):
  actual='HH2 Operating CCommittee Pack\nStabilize-and-RRecover RRebaseline'
  expected='H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'
  states=[actual]
  commands=[]
  for _ in range(8):
   current=states[-1]
   if current==expected:
    break
   plan=shim._task091_restricted_repair_plan(current,expected)
   self.assertTrue(plan)
   op=plan[0]
   command=shim._task091_restricted_repair_command([op])
   self.assertLessEqual(len(command.splitlines()),5)
   self.assertEqual(command.splitlines()[0], "pyautogui.hotkey('ctrl', 'a')")
   self.assertEqual(command.count("press('delete')")+command.count("hotkey('shift', 'enter')"),1)
   commands.append(command)
   states.append(shim._task091_apply_repair_operation(current,op))
  self.assertEqual(states[-1],expected)
  self.assertEqual(len(states)-1,4)
  self.assertEqual([shim._task091_restricted_repair_plan(s,expected)[0]['index']
                    for s in states[:-1]],[1,14,43,51])
  self.assertTrue(all('pyautogui.write(' not in command for command in commands))

 def test_task091_geometry_hint_disambiguates_repeated_text_and_table_cells(self):
  deck={
   'screen':[0,0,1920,1080],
   'window':{'bbox':[70,27,1850,1053]},
   'deck_file':{'slide_size':{'w':12191365,'h':6858000}},
   'deck_slide_shapes':{'9':[
    {'id':34,'name':'RoadmapLaneName_1','text':'Expansion Sprint',
     'geometry':{'x':804672,'y':2798063,'w':914400,'h':201168},'kind':'shape'},
    {'id':42,'name':'RoadmapBarText_1','text':'Expansion Sprint',
     'geometry':{'x':3127248,'y':2798064,'w':4224528,'h':164592},'kind':'shape'},
    {'id':-50101,'name':'KpiTable#r1c1','text':'Expansion Sprint',
     'geometry':{'x':6500000,'y':2800000,'w':900000,'h':200000},'kind':'table-cell'},
   ]}
  }
  left_shape=shim._task091_shape_for_old(deck,9,'Expansion Sprint',505,455)
  right_shape=shim._task091_shape_for_old(deck,9,'Expansion Sprint',901,453)
  self.assertIsNotNone(left_shape)
  self.assertIsNotNone(right_shape)
  self.assertEqual(left_shape['id'],34)
  self.assertEqual(right_shape['id'],42)
  self.assertNotEqual(left_shape['id'],right_shape['id'])
  left_center=shim._task091_shape_center(deck,left_shape)
  right_center=shim._task091_shape_center(deck,right_shape)
  self.assertIsNotNone(left_center)
  self.assertIsNotNone(right_center)
  left_hit=shim._task091_shape_text_point(deck,left_shape,left_center['cx'],left_center['cy'])
  right_hit=shim._task091_shape_text_point(deck,right_shape,right_center['cx'],right_center['cy'])
  self.assertIsNotNone(left_hit)
  self.assertIsNotNone(right_hit)
  self.assertEqual(left_hit['shape']['id'],34)
  self.assertEqual(right_hit['shape']['id'],42)

 def test_task091_repair_always_enters_text_mode_before_destructive_keys(self):
  command=shim._task091_restricted_repair_command([{'op':'delete','index':51,'char':'R'}])
  lines=command.splitlines()
  self.assertEqual(lines[0],"pyautogui.hotkey('ctrl', 'a')")
  self.assertEqual(lines[1],"pyautogui.press('left')")
  self.assertLessEqual(len(lines),6)


 def test_task091_focal_artifact_uses_signed_text_hit_not_empty_shape_center(self):
  deck={
   'schema':1,'stable':True,
   'screen':[0,0,1920,1080],
   'window':{'id':1,'pid':1,'title':'Operating_Committee_Rebaseline_Draft.pptx - WPS Office',
             'owner_title':'','wm_class':'wpp wpp','bbox':[70,27,1850,1053]},
   'deck_slide_text':{'1':'H2 Operating Committee Pack Growth Plan Draft'},
   'deck_slide_shapes':{'1':[{
      'id':6,'name':'CoverTitle','text':'H2 Operating Committee Pack\nGrowth Plan Draft',
      'geometry':{'x':749808,'y':1078992,'w':5852160,'h':1234440}}]},
   'deck_file':{'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                'sha256':'4c9c57567fa8f4bd81175dbd3d1b2ea40f0ad1ff8689ca47e1cbd001da637f5b',
                'slide_size':{'w':12192000,'h':6858000}}
  }
  center=shim._task091_shape_center(deck,deck['deck_slide_shapes']['1'][0])
  hit=shim._task091_shape_point(deck,1,'Growth Plan Draft',745,335)
  self.assertIsNotNone(center)
  self.assertIsNotNone(hit)
  self.assertEqual([hit['cx'],hit['cy']],[745,335])
  self.assertNotEqual([hit['cx'],hit['cy']],[center['cx'],center['cy']])
  self.assertEqual([center['cx'],center['cy']],[869,390])
  self.assertIsNone(shim._task091_shape_point(deck,1,'Growth Plan Draft',1400,800))

 def test_task091_writer_never_uses_f2_after_signed_text_hit(self):
  command=shim._task091_write_command('H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline')
  self.assertNotIn("press('f2')",command)
  self.assertEqual(command.splitlines()[0],"pyautogui.hotkey('ctrl', 'a')")
  with self.assertRaisesRegex(ValueError,'TASK091_TEXT_MODE_MUST_BE_POINTER_ESTABLISHED'):
   shim._task091_write_command('x',ensure_text_mode=True)


if __name__=='__main__':unittest.main()
