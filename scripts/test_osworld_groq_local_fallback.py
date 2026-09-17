import os
import unittest
from unittest.mock import patch

from osworld_groq_free import GroqFreeRoute, MODELS

BODY = {
    'instruction': 'Dismiss the visible menu',
    'observation': 'menu visible',
    'screenshot_data_url': 'data:image/png;base64,fixture',
}
LOCAL_ACTION = {
    'provider': 'local-cloud-vlm',
    'model': 'local-test',
    'action': {'action': 'exec', 'command': "pyautogui.press('esc')"},
}


class GroqLocalFallbackTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            'ZERO_SPEND_MODE': 'HARD',
            'ARBM_ENABLE_LOCAL_VLM': '1',
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.now = 100.0
        self.requests = []
        self.route = GroqFreeRoute(self.transport, lambda: self.now)

    def transport(self, path, key, payload=None, timeout=35):
        self.requests.append((path, timeout))
        return 429, {}, {'retry-after': '60'}

    def test_quota_exhaustion_uses_local_before_returning_failure(self):
        local_attempt = {
            'route': 'local-cloud-vlm',
            'model': 'local-test',
            'status': 200,
            'zero_spend_confirmed': True,
            'mandatory_cost_usd': 0,
            'paid_fallback_used': False,
        }
        with patch('osworld_groq_free.LOCAL_VLM_ROUTE.call',
                   return_value=(LOCAL_ACTION, [local_attempt])) as local:
            result, attempts = self.route.call(BODY, 'free-key', budget=55)
        self.assertEqual(result['provider'], 'local-cloud-vlm')
        self.assertTrue(local.called)
        self.assertEqual(local.call_args.kwargs['budget'], 35.0)
        self.assertTrue(any(x.get('status') == 429 for x in attempts))
        self.assertEqual(attempts[-1]['mandatory_cost_usd'], 0)
        self.assertFalse(attempts[-1]['paid_fallback_used'])

    def test_groq_keeps_reserved_time_for_local_fallback(self):
        local_attempt = {
            'route': 'local-cloud-vlm',
            'model': 'local-test',
            'status': 'local_model_error',
            'mandatory_cost_usd': 0,
            'paid_fallback_used': False,
        }
        with patch('osworld_groq_free.LOCAL_VLM_ROUTE.call',
                   return_value=(None, [local_attempt])):
            result, attempts = self.route.call(BODY, 'free-key', budget=55)
        self.assertIsNone(result)
        self.assertLessEqual(len(self.requests), len(MODELS))
        self.assertTrue(all(timeout <= 20 for _, timeout in self.requests))
        self.assertEqual(attempts[-1]['route'], 'local-cloud-vlm')

    def test_missing_groq_key_still_uses_quota_independent_local(self):
        local_attempt = {
            'route': 'local-cloud-vlm',
            'model': 'local-test',
            'status': 200,
            'zero_spend_confirmed': True,
            'mandatory_cost_usd': 0,
            'paid_fallback_used': False,
        }
        with patch('osworld_groq_free.LOCAL_VLM_ROUTE.call',
                   return_value=(LOCAL_ACTION, [local_attempt])):
            result, attempts = self.route.call(BODY, '', budget=50)
        self.assertEqual(result['provider'], 'local-cloud-vlm')
        self.assertEqual(attempts[0]['status'], 'not_configured')
        self.assertEqual(len(self.requests), 0)


if __name__ == '__main__':
    unittest.main()
