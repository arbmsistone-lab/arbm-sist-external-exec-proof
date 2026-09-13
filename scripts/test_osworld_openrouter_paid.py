import json
import os
import unittest
from unittest.mock import patch

from osworld_control import validate_response
from osworld_openrouter_paid import PaidRoute, DEFAULT_MODEL


class PaidRouteTests(unittest.TestCase):
    def env(self, **extra):
        values={
            'ARBM_VALIDATION_SPEND_MODE':'paid-bounded',
            'OPENROUTER_API_KEY':'test-key',
            'ARBM_PAID_MODEL':DEFAULT_MODEL,
            'ARBM_PAID_TOTAL_BUDGET_USD':'0.50',
            'ARBM_PAID_REQUEST_MAX_USD':'0.05',
        }
        values.update(extra)
        return patch.dict(os.environ, values, clear=False)

    def test_paid_route_enforces_privacy_provider_and_budget(self):
        seen={}
        def transport(path,key,payload=None,timeout=35):
            seen.update(payload)
            body={'action':'exec','command':"pyautogui.press('esc')"}
            return 200,{'choices':[{'message':{'content':json.dumps(body)}}],
                       'usage':{'cost':0.003},'provider':'google-vertex/us-east5'},{}
        with self.env():
            result,attempts=PaidRoute(transport=transport).call({'screenshot_data_url':'data:image/png;base64,AA=='})
        self.assertIsNotNone(result)
        self.assertEqual(result['model'],DEFAULT_MODEL)
        self.assertTrue(result['paid_fallback_used'])
        self.assertEqual(seen['provider']['data_collection'],'deny')
        self.assertTrue(seen['provider']['zdr'])
        self.assertEqual(seen['provider']['only'],['google-vertex','google-ai-studio'])
        self.assertEqual(seen['response_format'],{'type':'json_object'})
        self.assertTrue(attempts[-1]['paid_route_proven'])

    def test_paid_route_rejects_request_above_cap(self):
        def transport(path,key,payload=None,timeout=35):
            body={'action':'exec','command':"pyautogui.press('esc')"}
            return 200,{'choices':[{'message':{'content':json.dumps(body)}}],
                       'usage':{'cost':0.051},'provider':'google-vertex'},{}
        with self.env():
            result,attempts=PaidRoute(transport=transport).call({'screenshot_data_url':'data:image/png;base64,AA=='})
        self.assertIsNone(result)
        self.assertEqual(attempts[-1]['contract_error'],'PAID_BUDGET_EXCEEDED')

    def test_paid_response_validation_requires_paid_proof(self):
        data={'pipeline':'p','agent_build':'b','ok':True,'model':DEFAULT_MODEL,
              'mandatory_cost_usd':0.003,'paid_fallback_used':True,
              'provider_attempts':[{'model':DEFAULT_MODEL,'status':200,'paid_route_proven':True}]}
        with self.env():
            validate_response(data,'p','b')


if __name__=='__main__':
    unittest.main()
