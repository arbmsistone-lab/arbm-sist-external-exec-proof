import json
import os
import unittest
from unittest.mock import patch
from osworld_openrouter_free import FreeRoute, eligible, PREFERRED, MAX_FREE_CANDIDATES, FREE_ROUTER_MODEL

MODEL={'id':PREFERRED[0], 'pricing':{'prompt':'0','completion':'0'},
       'architecture':{'input_modalities':['text','image'],'output_modalities':['text']},
       'context_length':262144, 'supported_parameters':['response_format']}
BODY={'instruction':'Inspect the visible menu', 'screenshot_data_url':'data:image/png;base64,real-unit-fixture'}
ACTION={'action':'exec','command':"pyautogui.press('esc')"}


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD'}); self.env.start()
        self.addCleanup(self.env.stop)
        self.now=100; self.requests=[]
        self.replies=[]
        self.route=FreeRoute(self.transport,lambda:self.now)

    def transport(self,path,key,payload=None,timeout=35):
        self.requests.append((path,payload))
        if path=='/key':return 200,{'data':{'is_free_tier':True}},{}
        if path=='/models':return 200,{'data':[MODEL,dict(MODEL,id=PREFERRED[1])]},{}
        return self.replies.pop(0) if self.replies else (503,{}, {})

    def answer(self,cost=0,action=ACTION):
        return 200,{'usage':{'cost':cost},'choices':[{'message':{'content':json.dumps(action)}}]},{}

    def test_cost_and_request_are_both_guarded(self):
        self.replies=[self.answer()]
        result,attempts=self.route.call(BODY,'test-key')
        self.assertEqual(result['action']['action'],'exec')
        self.assertTrue(attempts[-1]['free_plan_proven'])
        payload=self.requests[-1][1]
        self.assertTrue(payload['model'].endswith(':free'))
        self.assertTrue(all(x==0 for x in payload['provider']['max_price'].values()))
        self.assertNotIn('test-key',json.dumps(attempts))

    def test_paid_or_unproven_catalog_is_never_eligible(self):
        for pricing in ({'prompt':'0.1','completion':'0'}, {'prompt':'0'},
                        {'prompt':'NaN','completion':'0'}, {'prompt':'0','completion':'0','image':'1'}):
            self.assertFalse(eligible(dict(MODEL,pricing=pricing)))
        self.assertFalse(eligible(dict(MODEL,id='paid-model')))

    def test_nonzero_missing_and_nonfinite_response_cost_rejected(self):
        for cost in (1,None,float('nan'),False):
            with self.subTest(cost=cost):
                self.route=FreeRoute(self.transport,lambda:self.now)
                self.replies=[self.answer(cost),self.answer(cost)]
                result,attempts=self.route.call(BODY,'key')
                self.assertIsNone(result)
                self.assertFalse(any(a.get('free_plan_proven') for a in attempts))

    def test_429_fails_over_and_recovery_needs_real_probe(self):
        self.replies=[(429,{}, {'Retry-After':'60'}),self.answer()]
        result,_=self.route.call(BODY,'key')
        self.assertEqual(result['model'],PREFERRED[1])
        self.assertEqual(self.route.state(PREFERRED[0])['state'],'RATE_LIMITED')
        self.now+=61
        # A failed recovered route cannot become healthy by elapsed time alone.
        self.route.state(PREFERRED[1])['until']=self.now+100
        self.replies=[(503,{}, {})]
        result,_=self.route.call(BODY,'key')
        self.assertIsNone(result)
        self.assertNotEqual(self.route.state(PREFERRED[0])['state'],'HEALTHY')
        self.now+=61; self.route.state(FREE_ROUTER_MODEL)['until']=self.now+100; self.replies=[self.answer()]
        result,_=self.route.call(BODY,'key')
        self.assertEqual(result['model'],PREFERRED[0])
        self.assertEqual(self.route.state(PREFERRED[0])['state'],'HEALTHY')

    def test_catalog_admits_additional_verified_free_vision_models(self):
        extra = dict(MODEL, id='community/extra-vision:free')
        def transport(path,key,payload=None,timeout=35):
            if path=='/key': return 200,{'data':{'is_free_tier':True}},{}
            if path=='/models': return 200,{'data':[extra]},{}
            return self.answer()
        self.route=FreeRoute(transport,lambda:self.now)
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','OPENROUTER_API_KEY':'test'}):
            result,attempts=self.route.call(BODY,'test')
        self.assertEqual(result['model'],extra['id'])
        self.assertLessEqual(len(self.route.models),MAX_FREE_CANDIDATES)
        self.assertTrue(attempts[-1]['free_plan_proven'])

    def test_one_model_payment_error_does_not_block_other_free_routes(self):
        self.replies=[(402,{},{}),self.answer()]
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','OPENROUTER_API_KEY':'test'}):
            result,attempts=self.route.call(BODY,'test')
        self.assertEqual(result['model'],PREFERRED[1])
        self.assertEqual(attempts[-2]['status'],402)
        self.assertEqual(self.route.provider_until,0)

    def test_official_free_router_is_a_zero_price_last_resort(self):
        self.replies=[self.answer()]
        self.route.models=[]
        # The dynamic catalog includes the documented free router even when
        # no fixed preferred model is listed as available.
        def transport(path,key,payload=None,timeout=35):
            if path=='/key': return 200,{'data':{'is_free_tier':True}},{}
            if path=='/models': return 200,{'data':[]},{}
            return self.replies.pop(0)
        self.route=FreeRoute(transport,lambda:self.now)
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','OPENROUTER_API_KEY':'test'}):
            result,attempts=self.route.call(BODY,'test')
        self.assertEqual(result['model'],FREE_ROUTER_MODEL)
        self.assertTrue(attempts[-1]['free_plan_proven'])

    def test_auth_failure_disables_provider_and_no_billing_retry(self):
        self.replies=[(401,{}, {})]
        result,_=self.route.call(BODY,'key')
        count=len(self.requests)
        result,attempts=self.route.call(BODY,'key')
        self.assertIsNone(result);self.assertEqual(len(self.requests),count)
        self.assertEqual(attempts[0]['status'],'provider_cooldown')

    def test_non_gui_capability_never_becomes_action(self):
        self.replies=[self.answer(action={'action':'exec','command':'os.system("secret")'})]*2
        result,_=self.route.call(BODY,'key')
        self.assertIsNone(result)


if __name__=='__main__': unittest.main()
