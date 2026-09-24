import sys,unittest,tempfile,pathlib,importlib.util,copy,json
import os
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import osworld_free_mesh_shim as shim
REAL_REQUEST_MESH=shim.request_mesh
from osworld_control import Verifier, ground_action

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
  cover={
      'id':6,'name':'CoverTitle',
      'text':'H2 Operating Committee Pack\nGrowth Plan Draft',
      'paragraphs':['H2 Operating Committee Pack','Growth Plan Draft'],
      'kind':'shape','frame_id':0,'row':-1,'col':-1,
      'font_sizes':[2400],'fill_rgb':'',
      'geometry':{'x':749808,'y':1078992,'w':5852160,'h':1234440}}
  subtitle={
      'id':7,'name':'CoverSub',
      'text':'Northstar Cloud\nPrepared for July Operating Committee review\nPlanning posture: accelerate growth through H2 scale-up',
      'paragraphs':['Northstar Cloud','Prepared for July Operating Committee review',
                    'Planning posture: accelerate growth through H2 scale-up'],
      'kind':'shape','frame_id':0,'row':-1,'col':-1,
      'font_sizes':[1600],'fill_rgb':'',
      'geometry':{'x':768096,'y':2743200,'w':5669280,'h':1280160}}
  deck={'schema':1,'stable':True,'window':{
   'id':50331680,'pid':2689,'title':'Operating_Committee_Rebaseline_Draft.pptx - WPS Office',
   'owner_title':'','wm_class':'wpp wpp','bbox':[70,27,1850,1053]},
   'screen':[0,0,1920,1080],'active_slide':1,'screenshot_sha256':'1'*64,
   'deck_slide_text':{'1':'H2 Operating Committee Pack Growth Plan Draft Planning posture: accelerate growth through H2 scale-up'},
   'deck_slide_runs':{'1':['H2 Operating Committee Pack','Growth Plan Draft',
                           'Planning posture: accelerate growth through H2 scale-up']},
   'deck_slide_shapes':{'1':[cover,subtitle]},
   'deck_slide_charts':{},'deck_slide_relationships':{'1':[]},
   'deck_file':{'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                'sha256':'a'*64,'size':1234,'mtime_ns':1,
                'slide_size':{'w':12192000,'h':6858000}}}
  deck_obs='text\tGrowth Plan Draft\tGrowth Plan Draft\t\t\t(700, 300)\t(100, 40)'
  with patch.dict(os.environ,{'TASK_ID':'091','ZERO_SPEND_MODE':'HARD'},clear=False):
   # Modal recovery stays bounded and independent of semantic mutation.
   modal_state={'semantic_text_done':True,'section_e_format_done':True,
                'spatial_index':len(shim.TASK091_SPATIAL_TEXT_EDITS)}
   tab=shim.next_091_specialist_action(task,'WPS 2019','',modal_state,transient)
   space=shim.next_091_specialist_action(task,'WPS 2019','',modal_state,transient)
   self.assertEqual(tab['command'],"pyautogui.press('tab')")
   self.assertEqual(space['command'],"pyautogui.press('space')")
   self.assertNotIn("alt', 'f4",tab['command']+space['command'])
   anchor=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,modal_state,deck)
   self.assertEqual(anchor['command'],"pyautogui.hotkey('ctrl', 'home')")

   # One observed Close control is allowed; ambiguity remains fail-closed.
   fallback={}
   self.assertEqual(shim.next_091_specialist_action(task,'WPS 2019','',fallback,transient)['command'],
                    "pyautogui.press('tab')")
   self.assertEqual(shim.next_091_specialist_action(task,'WPS 2019','',fallback,transient)['command'],
                    "pyautogui.press('space')")
   transient_close={**transient,'controls':[{
      'label':'Close','role':'push button','pid':2689,'application':'wps',
      'bbox':[650,360,90,32],'showing':True,'enabled':True,'focused':True}]}
   click=shim.next_091_specialist_action(task,'WPS 2019','',fallback,transient_close)
   self.assertEqual(click['command'],'pyautogui.click(695, 376)')
   self.assertEqual(click['target']['source'],'accessibility')
   ambiguous={}
   shim.next_091_specialist_action(task,'WPS 2019','',ambiguous,transient)
   shim.next_091_specialist_action(task,'WPS 2019','',ambiguous,transient)
   two={**transient,'controls':[
      {'label':'Close','role':'push button','pid':2689,'application':'wps',
       'bbox':[650,360,90,32],'showing':True,'enabled':True,'focused':True},
      {'label':'Close','role':'push button','pid':2689,'application':'wps',
       'bbox':[500,360,90,32],'showing':True,'enabled':True,'focused':False}]}
   self.assertEqual(
      shim.next_091_specialist_action(task,'WPS 2019','',ambiguous,two)['reason'],
      'TASK091_TARGET_AMBIGUOUS')

   required={'$40.9M','$2.8M','104%','71%','17 mo','206','3',
             'Renewal saves','Pricing discipline','Migration delay','Support credits',
             'International Pilot stop','Partner stabilization','Platform','Reliability',
             'Protected hiring','Freeze','Vendor SLA breach','Data migration cutover failure',
             'Reliability Hardening','Data Migration','H2 Stabilize-and-Recover Roadmap',
             'Protect Reliability Hardening capacity','Sequence Data Migration cutover',
             'Freeze non-critical hiring','Incident runbook rollout','Cutover rehearsal complete',
             'Recovery review with OpCom'}
   self.assertTrue(required.issubset({row[4] for row in shim.TASK091_SPATIAL_TEXT_EDITS}))

   # Fresh Task 091 execution uses semantic_tx, never pending_edit/caret authority.
   state={'owned':True,'anchored':True,'slide':1,'spatial_index':0}
   select=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,deck)
   self.assertEqual(select.get('action'),'exec',select)
   self.assertEqual(select.get('specialist_phase'),'semantic-target-select',select)
   self.assertEqual(select['target']['source'],'task091-pptx-canonical')
   self.assertNotIn('pending_edit',state)
   self.assertEqual(state['semantic_tx']['stage'],'select-issued')

   preflight=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,deck)
   self.assertEqual(preflight['specialist_phase'],'semantic-cover-autofit-pane-open')
   self.assertIn("hotkey('shift', 'f10')",preflight['command'])
   self.assertIn("press('o')",preflight['command'])
   deck_pane=copy.deepcopy(deck)
   deck_pane['screenshot_sha256']='c'*64
   captured=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,deck_pane)
   self.assertEqual(captured['action'],'exec')
   self.assertEqual(captured['specialist_phase'],'semantic-cover-autofit-text-options-open')
   self.assertEqual(state['semantic_tx']['autofit_panel_points']['text_options'],[1730,219])
   self.assertEqual(state['semantic_tx']['autofit_panel_points']['text_box'],[1730,251])
   deck_textbox=copy.deepcopy(deck)
   deck_textbox['screenshot_sha256']='d'*64
   textbox_capture=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,deck_textbox)
   self.assertEqual(textbox_capture['reason'],'TASK091_COVERTITLE_TEXTBOX_PANE_CAPTURED')
   state['semantic_tx']['stage']='select-issued'
   state['semantic_tx']['autofit_preflight_done']=True
   mutation=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,deck)
   self.assertEqual(mutation['specialist_phase'],'semantic-text-mutation')
   self.assertIn("hotkey('ctrl', 'h')",mutation['command'])
   self.assertIn("Growth Plan Draft",mutation['command'])
   self.assertIn("Stabilize-and-Recover Rebaseline",mutation['command'])
   self.assertIn("hotkey('alt', 'a')",mutation['command'])
   self.assertNotIn("hotkey('ctrl', 'a')",mutation['command'])
   for forbidden in ("press('home')","press('left'","caret","ink_left"):
    self.assertNotIn(forbidden,mutation['command'].casefold())

   commit=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,deck)
   self.assertEqual(commit['specialist_phase'],'semantic-edit-finalize')
   save=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,deck)
   self.assertEqual(save['specialist_phase'],'semantic-save')

   final_cover=copy.deepcopy(cover)
   final_cover['text']='H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'
   final_cover['paragraphs']=['H2 Operating Committee Pack','Stabilize-and-Recover Rebaseline']
   deck_after=copy.deepcopy(deck)
   deck_after['deck_slide_shapes']['1'][0]=final_cover
   deck_after['deck_slide_text']['1']='H2 Operating Committee Pack Stabilize-and-Recover Rebaseline Planning posture: accelerate growth through H2 scale-up'
   deck_after['deck_file']['sha256']='b'*64
   reread=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,deck_after)
   self.assertEqual(reread['specialist_phase'],'semantic-roundtrip-reread')
   verified=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,state,deck_after)
   self.assertEqual(verified['checkpoint'],'TASK091_SEMANTIC_TRANSACTION_PASS')
   self.assertEqual(state['semantic_index'],1)
   self.assertTrue(verified['semantic_evidence']['diff_budget_exact'])
   self.assertTrue(verified['semantic_evidence']['no_collateral_mutation'])
   self.assertTrue(verified['semantic_evidence']['roundtrip'])
   self.assertNotIn('pending_edit',state)

   # Missing or ambiguous semantic targets fail closed without pixel/caret fallback.
   missing=copy.deepcopy(deck)
   missing['deck_slide_shapes']['1']=[subtitle]
   missing_state={'owned':True,'anchored':True,'slide':1,'spatial_index':0}
   miss=shim.next_091_specialist_action(task,'WPS Presentation','',missing_state,missing)
   self.assertEqual(miss['action'],'terminal')
   self.assertEqual(miss['reason'],'TASK091_TARGET_MISSING')

   duplicate=copy.deepcopy(cover); duplicate['id']=106
   ambiguous_deck=copy.deepcopy(deck)
   ambiguous_deck['deck_slide_shapes']['1'].append(duplicate)
   ambiguous_state={'owned':True,'anchored':True,'slide':1,'spatial_index':0}
   amb=shim.next_091_specialist_action(task,'WPS Presentation','',ambiguous_state,ambiguous_deck)
   self.assertEqual(amb['action'],'terminal')
   self.assertEqual(amb['reason'],'TASK091_TARGET_AMBIGUOUS')

   # Legacy pending_edit can exist for replay history but is forbidden in fresh execution.
   legacy={'owned':True,'anchored':True,'slide':1,
           'semantic_text_done':True,'section_e_format_done':True,
           'spatial_index':len(shim.TASK091_SPATIAL_TEXT_EDITS),
           'pending_edit':{'stage':'save-issued'}}
   blocked=shim.next_091_specialist_action(task,'WPS Presentation','',legacy,deck)
   self.assertEqual(blocked['action'],'terminal')
   self.assertEqual(blocked['reason'],'TASK091_LEGACY_TEXT_STATE_FORBIDDEN')

   # Handoff occurs only after the complete semantic plan and Section E are verified.
   done={'owned':True,'anchored':True,'slide':13,
         'spatial_index':len(shim.TASK091_SPATIAL_TEXT_EDITS),
         'semantic_text_done':True,'section_e_format_done':True}
   final_save=shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,done,deck)
   self.assertEqual(final_save['specialist_phase'],'semantic-pass-final-save')
   self.assertIsNone(shim.next_091_specialist_action(task,'WPS Presentation',deck_obs,done,deck))
   self.assertTrue(done.get('handoff'))
   self.assertEqual(done.get('handoff_reason'),
                    'SEMANTIC_TEXT_AND_SECTION_E_VERIFIED_CHART_FILL_REMAINS')

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
  self.assertEqual(verdict['status'],'PRE_FOCAL_ADVISORY_PASS')
  self.assertFalse(verdict['release_approval'])
  self.assertEqual(verdict['senior_pass'],50)
  self.assertEqual(verdict['master_pass'],10)
  unsafe=[{'op':'insert','index':27,'char':'S'}]
  with self.assertRaises(RuntimeError):
   evaluate(actual,expected,unsafe,shape,'a'*64,'b'*64)

 def test_task091_table_cell_suffix_duplicate_repair_is_single_char_fail_closed(self):
  cmd=shim._task091_table_cell_suffix_duplicate_repair_command('104%%','104%')
  self.assertEqual(cmd.splitlines()[0],"pyautogui.press('home')")
  self.assertIn("press('right', presses=4",cmd)
  self.assertEqual(cmd.count("press('delete')"),1)
  self.assertNotIn("ctrl', 'a",cmd)
  self.assertNotIn("keyDown('shift')",cmd)
  self.assertNotIn("backspace",cmd)
  self.assertNotIn("ctrl', 'z",cmd)
  for actual in ('%104%','104%%%','104%X','104'):
   with self.assertRaisesRegex(ValueError,'TASK091_TABLE_CELL_SUFFIX_REPAIR_NOT_PROVEN'):
    shim._task091_table_cell_suffix_duplicate_repair_command(actual,'104%')
  self.assertEqual(
   shim._task091_apply_repair_operation('104%%',{'op':'delete','index':4,'char':'%'}),
   '104%')

  cmd_currency=shim._task091_table_cell_suffix_duplicate_repair_command('$2.8MM','$2.8M')
  self.assertEqual(cmd_currency.splitlines()[0],"pyautogui.press('home')")
  self.assertIn("press('right', presses=5",cmd_currency)
  self.assertEqual(cmd_currency.count("press('delete')"),1)
  self.assertNotIn("ctrl', 'a",cmd_currency)
  self.assertEqual(
   shim._task091_apply_repair_operation('$2.8MM',{'op':'delete','index':5,'char':'M'}),
   '$2.8M')
  for actual in ('$2.8M','$2.8MMM','M$2.8M','$2.8MX'):
   with self.assertRaisesRegex(ValueError,'TASK091_TABLE_CELL_SUFFIX_REPAIR_NOT_PROVEN'):
    shim._task091_table_cell_suffix_duplicate_repair_command(actual,'$2.8M')

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


class Task091TransactionalTableCellTests(unittest.TestCase):
 def test_table_cell_writer_mutates_only_fixed_width_delta_from_proven_start(self):
  command=shim._task091_table_cell_bounded_write_command('$42.8M','$40.9M')
  self.assertNotIn("press('end')",command)
  self.assertNotIn("press('home')",command)
  self.assertNotIn("hotkey('ctrl', 'a')",command)
  self.assertNotIn("press('backspace'",command)
  self.assertNotIn("press('left'",command)
  self.assertNotIn("keyDown('shift')",command)
  self.assertNotIn("keyUp('shift')",command)
  self.assertEqual(command.count("press('delete')"),2)
  self.assertIn("press('right', presses=2",command)
  self.assertIn("write('0'",command)
  self.assertIn("write('9'",command)
  self.assertNotIn("write('$'",command)
  self.assertNotIn("write('M'",command)

 def test_slide3_all_six_kpis_use_bounded_same_length_delta_plans(self):
  pairs=(('$42.8M','$40.9M'),('112%','104%'),('74%','71%'),
         ('$2.6M','$2.8M'),('2','3'),('214','206'))
  for old,new in pairs:
   plan=shim._task091_table_cell_delta_plan(old,new)
   self.assertGreaterEqual(len(plan),1)
   self.assertLessEqual(len(plan),2)
   self.assertTrue(all(0 <= row['index'] < len(old) for row in plan))
   command=shim._task091_table_cell_bounded_write_command(old,new)
   self.assertNotIn("keyDown('shift')",command)
   self.assertNotIn("keyUp('shift')",command)
   self.assertNotIn("hotkey('ctrl', 'a')",command)
   self.assertNotIn("press('home')",command)
   self.assertNotIn("press('left'",command)
   self.assertEqual(command.count("press('delete')"),len(plan))

 def test_run35749283855_mid_text_caret_is_rejected_and_end_caret_is_proven(self):
  shape_bbox=[892,436,182,71]
  text_ink={'ink_bbox':[956,445,52,15],'proof_sha256':'a'*64}
  end=shim._task091_table_cell_text_end_point(text_ink,shape_bbox)
  self.assertIsNotNone(end)
  self.assertEqual([end['cx'],end['cy']],[1011,452])
  mid={'proven':True,'bbox':[91,3,1,22]}
  rejected=shim._task091_caret_at_text_end(mid,shape_bbox,text_ink['ink_bbox'],end['cx'])
  self.assertFalse(rejected['proven'],rejected)
  self.assertEqual(rejected['caret_x'],983)
  at_end={'proven':True,'bbox':[119,3,1,22]}
  accepted=shim._task091_caret_at_text_end(at_end,shape_bbox,text_ink['ink_bbox'],end['cx'])
  self.assertTrue(accepted['proven'],accepted)
  self.assertEqual(accepted['caret_x'],1011)

 def test_table_cell_rollback_requires_original_text_and_unchanged_siblings(self):
  base={'deck_file':{'sha256':'a'*64},'deck_slide_shapes':{'3':[
    {'id':-13001003,'name':'Table 12#r1c2','text':'$42.8M','kind':'table-cell','geometry':{}},
    {'id':-13001004,'name':'Table 12#r1c3','text':'Ahead','kind':'table-cell','geometry':{}},
  ]}}
  pending={'slide':3,'shape_id':-13001003,'old':'$42.8M','rollback_corrupt_deck_sha256':'b'*64}
  pending['before_sibling_signature']=shim._task091_other_shapes_signature(base,3,-13001003)
  corrupt=copy.deepcopy(base); corrupt['deck_file']['sha256']='b'*64
  corrupt['deck_slide_shapes']['3'][0]['text']='$40.9MM'
  self.assertFalse(shim._task091_table_cell_rollback_verified(pending,corrupt))
  restored=copy.deepcopy(base); restored['deck_file']['sha256']='c'*64
  self.assertTrue(shim._task091_table_cell_rollback_verified(pending,restored))
  collateral=copy.deepcopy(restored); collateral['deck_slide_shapes']['3'][1]['text']='Changed'
  self.assertFalse(shim._task091_table_cell_rollback_verified(pending,collateral))

 def test_table_cell_rollback_command_is_single_undo_persist_transaction(self):
  command=shim._task091_table_cell_rollback_command()
  self.assertEqual(command.count("hotkey('ctrl', 'z')"),1)
  self.assertEqual(command.count("hotkey('ctrl', 's')"),1)
  self.assertNotIn('pyautogui.write(',command)
  from osworld_control import canonical_action
  self.assertEqual(canonical_action({'action':'exec','command':command})['command'],command)

 def test_table_cell_start_navigation_moves_left_by_exact_text_length(self):
  command=shim._task091_table_cell_start_navigation_command('$42.8M')
  self.assertEqual(command,"pyautogui.press('left', presses=6, interval=0.03)")
  self.assertEqual(command.count("press('left'"),1)
  self.assertNotIn("click(",command)
  self.assertNotIn("press('home')",command)
  self.assertNotIn("keyDown('shift')",command)
  self.assertNotIn("press('right'",command)
  self.assertNotIn("pyautogui.write(",command)
  with self.assertRaisesRegex(ValueError,'TASK091_TABLE_CELL_START_NAV_TEXT_INVALID'):
   shim._task091_table_cell_start_navigation_command('')
  with self.assertRaisesRegex(ValueError,'TASK091_TABLE_CELL_START_NAV_TEXT_INVALID'):
   shim._task091_table_cell_start_navigation_command('x'*31)

 def test_table_cell_start_navigation_action_is_nonpointer_and_compiles_exactly(self):
  command=shim._task091_table_cell_start_navigation_command('214')
  action={'action':'exec','command':command,
          'plan':'From proven end, move left by exact text length.'}
  compiled=ground_action(action,'WPS Presentation','',allow_canonical=True)
  self.assertEqual(compiled['command'],"pyautogui.press('left', presses=3, interval=0.03)")
  self.assertNotIn('target',compiled)

 def test_table_cell_delta_edit_never_touches_terminal_marker(self):
  self.assertEqual(shim._task091_table_cell_selection_presses('$42.8M'),6)
  command=shim._task091_table_cell_bounded_write_command('x'*30,'x'*29+'y')
  self.assertIn("press('right', presses=29",command)
  self.assertNotIn("press('right', presses=30",command)
  self.assertEqual(command.count("press('delete')"),1)
  self.assertNotIn("press('left'",command)
  self.assertNotIn("keyDown('shift')",command)

 def test_table_cell_start_caret_guard_and_single_marker_normalization(self):
  shape_bbox=[892,507,182,70]; ink_bbox=[965,516,35,12]
  at_start=shim._task091_caret_at_text_start({'proven':True,'bbox':[72,2,1,22]},shape_bbox,ink_bbox)
  self.assertTrue(at_start['proven'],at_start)
  self.assertEqual(at_start['relation'],'at-start')
  marker_offset=shim._task091_caret_at_text_start({'proven':True,'bbox':[80,2,1,22]},shape_bbox,ink_bbox)
  self.assertFalse(marker_offset['proven'],marker_offset)
  self.assertEqual(marker_offset['relation'],'right-of-start')
  source=pathlib.Path('scripts/osworld_free_mesh_shim.py').read_text(encoding='utf-8')
  self.assertIn("normalize_attempts < 1",source)
  self.assertIn("normalize-wps-terminal-marker-offset",source)

 def test_section_e_font_correction_is_semantic_and_caret_free(self):
  spec=shim.TASK091_SECTION_E_FORMAT
  self.assertEqual(spec['slide'],3)
  self.assertEqual(spec['shape_id'],16)
  self.assertEqual(spec['shape_name'],'KpiReadout_Body')
  self.assertEqual(spec['font_decrements'],2)
  source=pathlib.Path('scripts/osworld_free_mesh_shim.py').read_text(encoding='utf-8')
  body=source.split("def _task091_section_e_format_step",1)[1].split(
      "def _task091_system_check_close",1)[0]
  self.assertIn("task091_verify_font_transaction",body)
  self.assertIn("section-e-semantic-roundtrip",body)
  self.assertIn("pyautogui.hotkey('ctrl', '[')",body)
  self.assertNotIn("_task091_caret",body)
  self.assertNotIn("CARET_UNPROVEN",body)

 def test_section_e_postsave_accepts_only_bounded_target_autofit_shrink(self):
  before={'x':9034272,'y':1883664,'w':2148840,'h':1353312}
  observed={'x':9034272,'y':1883664,'w':2148840,'h':922020}
  self.assertTrue(shim._task091_section_e_geometry_persisted(before,observed))
  self.assertTrue(shim._task091_section_e_geometry_persisted(before,before))
  self.assertFalse(shim._task091_section_e_geometry_persisted(before,{**observed,'x':observed['x']+1}))
  self.assertFalse(shim._task091_section_e_geometry_persisted(before,{**observed,'w':observed['w']-1}))
  self.assertFalse(shim._task091_section_e_geometry_persisted(before,{**observed,'h':before['h']+1}))
  self.assertFalse(shim._task091_section_e_geometry_persisted(before,{**observed,'h':int(before['h']*0.59)}))

 def test_500_case_two_delta_red_team_matrix(self):
  alphabet="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz$%.-_"
  for i in range(500):
   n=(i % 30)+1
   old=''.join(alphabet[(i*7+j*11) % len(alphabet)] for j in range(n))
   chars=list(old); first=i % n
   chars[first]=alphabet[(alphabet.index(chars[first])+1) % len(alphabet)]
   if n>1 and i % 2:
    second=(first+max(1,n//2)) % n
    if second==first: second=(first+1)%n
    chars[second]=alphabet[(alphabet.index(chars[second])+2) % len(alphabet)]
   new=''.join(chars)
   plan=shim._task091_table_cell_delta_plan(old,new)
   self.assertLessEqual(len(plan),2)
   command=shim._task091_table_cell_bounded_write_command(old,new)
   self.assertEqual(command.count("press('delete')"),len(plan))
   self.assertNotIn("keyDown('shift')",command)
   self.assertNotIn("hotkey('ctrl', 'a')",command)
   self.assertNotIn("press('left'",command)

 def test_table_cell_atomic_repair_handles_multi_edge_corruption_one_delete_at_a_time(self):
  actual='$$40.9MM'; expected='$40.9M'
  plan=shim._task091_restricted_repair_plan(actual,expected)
  self.assertEqual(plan,[{'op':'delete','index':1,'char':'$'},{'op':'delete','index':6,'char':'M'}])
  first=shim._task091_table_cell_atomic_delete_repair_command(actual,plan[0])
  self.assertIn("press('right', presses=1",first)
  self.assertEqual(first.count("press('delete')"),1)
  after=shim._task091_apply_repair_operation(actual,plan[0])
  self.assertEqual(after,'$40.9MM')
  next_plan=shim._task091_restricted_repair_plan(after,expected)
  self.assertEqual(next_plan,[{'op':'delete','index':6,'char':'M'}])


if __name__=='__main__':unittest.main()