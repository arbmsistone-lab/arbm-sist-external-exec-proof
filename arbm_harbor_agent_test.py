import importlib.util, json, os, sys, unittest
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

class Tests(unittest.TestCase):
 def test_sovereign_contract_is_zero_cost(self):
  payload=json.dumps({'choices':[{'message':{'content':'{"action":"exec","command":"pwd","summary":"inspect"}'}}]}).encode()
  class Response:
   def __enter__(self): return self
   def __exit__(self,*a): return False
   def read(self): return payload
  with patch.object(agent.urllib.request,'urlopen',return_value=Response()):
   out=agent.ARBMHarborAgent()._sovereign_decide('inspect','none',1)
  self.assertEqual(out['action']['command'],'pwd'); self.assertEqual(out['mandatory_cost_usd'],0); self.assertFalse(out['paid_fallback_used']); self.assertEqual(out['provider'],'sovereign-qwen-github')
 def test_remote_failure_uses_sovereign_only_when_enabled(self):
  a=agent.ARBMHarborAgent()
  with patch.object(a,'_oidc',return_value='token'), patch.object(agent.urllib.request,'urlopen',side_effect=agent.urllib.error.URLError('offline')), patch.object(a,'_sovereign_decide',return_value={'ok':True,'action':{'action':'finish','summary':'ok'},'mandatory_cost_usd':0,'paid_fallback_used':False}) as sovereign, patch.object(agent.time,'sleep'):
   with patch.dict(os.environ,{'ARBM_ENABLE_SOVEREIGN_FALLBACK':'1'}): self.assertTrue(a._decide('x','y',1)['ok'])
   sovereign.assert_called_once()

 def test_http_422_is_retried_immediately(self):
  a=agent.ARBMHarborAgent()
  bad=agent.urllib.error.HTTPError("x",422,"invalid",{},None); bad.read=lambda: json.dumps({"status":"INVALID_ACTION","provider_attempts":[]}).encode()
  good_payload=json.dumps({"ok":True,"action":{"action":"finish","command":"","summary":"ok"},"mandatory_cost_usd":0,"paid_fallback_used":False}).encode()
  class Response:
   def __enter__(self): return self
   def __exit__(self,*a): return False
   def read(self): return good_payload
  with patch.object(a,"_oidc",return_value="token"), patch.object(agent.urllib.request,"urlopen",side_effect=[bad,Response()]), patch.object(agent.time,"sleep") as sleeper:
   out=a._decide("x","y",1)
  self.assertTrue(out["ok"]); sleeper.assert_not_called()


 def test_long_groq_reset_opens_remote_circuit(self):
  a=agent.ARBMHarborAgent()
  body=json.dumps({"status":"WAITING_FREE_CAPACITY","provider_attempts":[{"route":"groq-json-object","status":429,"retry_after":"433"}]}).encode()
  exc=agent.urllib.error.HTTPError("x",503,"busy",{},None); exc.read=lambda: body
  sovereign={"ok":True,"action":{"action":"finish","summary":"fallback"},"mandatory_cost_usd":0,"paid_fallback_used":False}
  with patch.object(a,"_oidc",return_value="token"), patch.object(agent.urllib.request,"urlopen",side_effect=exc), patch.object(a,"_sovereign_decide",return_value=sovereign) as sv, patch.object(agent.time,"sleep"):
   with patch.dict(os.environ,{"ARBM_ENABLE_SOVEREIGN_FALLBACK":"1"}): out=a._decide("x","y",1)
  self.assertTrue(out["ok"]); self.assertGreater(getattr(a,"_remote_cooldown_until",0),0); sv.assert_called_once()

if __name__=='__main__': unittest.main()
