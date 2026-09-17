import json
import os
import unittest
from unittest.mock import patch
from osworld_groq_free import GroqFreeRoute, MODELS

BODY={'instruction':'Dismiss the visible menu', 'screenshot_data_url':'data:image/png;base64,fixture'}
ACTION={'action':'exec','command':"pyautogui.press('esc')"}


class GroqFreeTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD'});self.env.start();self.addCleanup(self.env.stop)
        self.now=100;self.requests=[];self.replies=[]
        self.route=GroqFreeRoute(self.transport,lambda:self.now)

    def transport(self,path,key,payload=None,timeout=35):
        self.requests.append((path,payload))
        return self.replies.pop(0)

    @staticmethod
    def answer(action=ACTION):
        return 200,{'choices':[{'message':{'content':json.dumps(action)}}]}, {'x-ratelimit-remaining-requests':'999','x-ratelimit-limit-requests':'1000','x-ratelimit-limit-tokens':'8000'}

    def test_free_vision_result_requires_parsed_gui_action(self):
        self.replies=[self.answer()]
        result,attempts=self.route.call(BODY,'free-key')
        self.assertEqual(result['provider'],'groq-free')
        self.assertEqual(result['model'],MODELS[0])
        self.assertTrue(attempts[-1]['zero_spend_confirmed'])
        self.assertEqual(self.requests[-1][1]['response_format'],{'type':'json_object'})

    def test_rate_limit_fails_over_to_second_free_model(self):
        self.replies=[(429,{},{}),self.answer()]
        result,attempts=self.route.call(BODY,'free-key')
        self.assertEqual(result['model'],MODELS[1])
        self.assertEqual(attempts[0]['status'],429)

    def test_unparsed_response_is_not_promoted(self):
        invalid=[
            self.answer({'action':'exec','command':'os.system("bad")'}),
            self.answer({'action':'exec','command':'subprocess.run("bad")'}),
            self.answer({'action':'exec','command':'open("bad")'}),
            self.answer({'action':'exec','command':'eval("bad")'}),
        ]
        self.replies=invalid[:len(MODELS)]
        result,attempts=self.route.call(BODY,'free-key')
        self.assertIsNone(result)
        self.assertEqual(len(attempts),len(MODELS))
        self.assertFalse(any(x['zero_spend_confirmed'] for x in attempts))

    def test_model_scoped_403_fails_over_to_next_free_model(self):
        self.replies=[(403,{},{}), self.answer()]
        result,attempts=self.route.call(BODY,'key')
        self.assertIsNotNone(result)
        self.assertEqual(result['model'],MODELS[1])
        self.assertEqual(attempts[0]['status'],403)
        self.assertEqual(self.route.until,0)

    def test_http_200_without_free_plan_proof_is_rejected(self):
        first=(200,{'choices':[{'message':{'content':json.dumps(ACTION)}}]},{'x-ratelimit-remaining-requests':'9'})
        self.replies=[first]+[(429,{},{}) for _ in MODELS[1:]]
        result,attempts=self.route.call(BODY,'free-key')
        self.assertIsNone(result)
        self.assertEqual(len(attempts),len(MODELS))
        self.assertFalse(attempts[0]['free_plan_proven'])
        self.assertEqual(attempts[0]['contract_error'],'FREE_PLAN_PROOF_MISSING')


if __name__=='__main__':unittest.main()
