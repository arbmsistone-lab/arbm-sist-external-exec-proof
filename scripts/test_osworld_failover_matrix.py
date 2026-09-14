import os, pathlib, sys, unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import osworld_free_mesh_shim as shim

BODY={'instruction':'edit image','observation':'GIMP canvas','screenshot_data_url':'data:image/png;base64,AA=='}

def result(provider,model='free'):
 return {'provider':provider,'model':model,'action':{'action':'exec','command':"pyautogui.press('enter')"}}

def attempts(route,status=429):
 return [{'route':route,'model':'free','status':status,'mandatory_cost_usd':0,'paid_fallback_used':False}]

class FailoverMatrix(unittest.TestCase):
 def setUp(self):
  self.env=patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','ARBM_VALIDATION_SPEND_MODE':'zero'})
  self.env.start();self.addCleanup(self.env.stop)

 def test_openrouter_failure_immediately_advances_to_groq(self):
  with patch.object(shim.FREE_ROUTE,'call',return_value=(None,attempts('openrouter-multimodal-free'))), \
       patch.object(shim.GROQ_FREE_ROUTE,'call',return_value=(result('groq-free'),attempts('groq-multimodal-free',200))) as groq, \
       patch.object(shim,'request_gateway',side_effect=AssertionError('gateway should not run')):
   http,data=shim.request_mesh(dict(BODY))
  self.assertEqual((http,data['provider']),(200,'groq-free'));self.assertTrue(groq.called)
 def test_openrouter_and_groq_failure_advances_to_gateway(self):
  gateway={'ok':True,'status':'PASS','pipeline':shim.EXPECTED_PIPELINE,'agent_build':shim.EXPECTED_BUILD,
           'provider':'gateway-free','model':'g','action':{'action':'exec','command':"pyautogui.press('enter')"},
           'mandatory_cost_usd':0,'paid_fallback_used':False,'provider_attempts':[]}
  with patch.object(shim.FREE_ROUTE,'call',return_value=(None,attempts('openrouter-multimodal-free'))), \
       patch.object(shim.GROQ_FREE_ROUTE,'call',return_value=(None,attempts('groq-multimodal-free'))), \
       patch.object(shim,'request_gateway',return_value=(200,gateway)) as gw:
   http,data=shim.request_mesh(dict(BODY))
  self.assertEqual((http,data['provider']),(200,'gateway-free'));self.assertTrue(gw.called)

 def test_remote_capacity_failure_advances_to_local(self):
  local=result('local-cloud-vlm','local')
  with patch.object(shim.FREE_ROUTE,'call',return_value=(None,attempts('openrouter-multimodal-free'))), \
       patch.object(shim.GROQ_FREE_ROUTE,'call',return_value=(None,attempts('groq-multimodal-free'))), \
       patch.object(shim,'request_gateway',return_value=(503,{'status':'NO_ZERO_SPEND_MULTIMODAL_CAPACITY','provider_attempts':[]})), \
       patch.object(shim.LOCAL_VLM_ROUTE,'call',return_value=(local,[{'route':'local-cloud-vlm','model':'local','status':200,'zero_spend_confirmed':True}])):
   http,data=shim.request_mesh(dict(BODY))
  self.assertEqual((http,data['provider']),(200,'local-cloud-vlm'))

 def test_total_outage_reports_mesh_exhaustion_not_wait(self):
  none=(None,attempts('free-route'))
  with patch.object(shim.FREE_ROUTE,'call',return_value=none),patch.object(shim.GROQ_FREE_ROUTE,'call',return_value=none), \
       patch.object(shim,'request_gateway',return_value=(503,{'status':'NO_ZERO_SPEND_MULTIMODAL_CAPACITY','provider_attempts':[]})), \
       patch.object(shim.LOCAL_VLM_ROUTE,'call',return_value=(None,[{'route':'local-cloud-vlm','status':'local_model_error'}])):
   http,data=shim.request_mesh(dict(BODY))
  self.assertEqual(http,503);self.assertEqual(data['status'],'FREE_MESH_EXHAUSTED_CURRENT_CYCLE')
  self.assertFalse(data['paid_fallback_used']);self.assertEqual(data['mandatory_cost_usd'],0)

if __name__=='__main__':unittest.main()
