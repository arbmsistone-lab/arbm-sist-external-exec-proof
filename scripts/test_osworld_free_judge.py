import copy
import json
import os
import unittest
from unittest.mock import patch
from osworld_free_judge import complete
from osworld_openrouter_free import FreeRoute, PREFERRED


class JudgeTests(unittest.TestCase):
    def test_official_messages_and_negative_response_unchanged(self):
        messages=[{'role':'system','content':'Output MUST be exactly one token: YES or NO.'},
            {'role':'user','content':[{'type':'text','text':'Does the second image retain the first image style?'},
                                     {'type':'image_url','image_url':{'url':'data:image/png;base64,input','detail':'high'}}]}]
        original=copy.deepcopy(messages);requests=[]
        response={'id':'real-unit-response-fixture','model':PREFERRED[0],
            'choices':[{'message':{'content':'NO'}}],'usage':{'cost':0}}
        def transport(path,key,payload=None,timeout=35):
            if path=='/key':return 200,{'data':{'is_free_tier':True}},{}
            if path=='/models':return 200,{'data':[{'id':PREFERRED[0],
                'pricing':{'prompt':'0','completion':'0'},'context_length':262144,
                'architecture':{'input_modalities':['text','image'],'output_modalities':['text']}}]},{}
            requests.append(payload);return 200,response,{}
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','OPENROUTER_API_KEY':'test'}):
            result,attempts=complete({'messages':messages,'max_completion_tokens':10,'temperature':0},FreeRoute(transport))
        self.assertEqual(messages,original);self.assertEqual(requests[0]['messages'],original)
        self.assertEqual(requests[0]['max_tokens'],10)
        self.assertEqual(result['text'],'NO');self.assertEqual(result['raw_response'],response)
        self.assertEqual(len(requests),1,'NO must never trigger a retry seeking approval')
        self.assertNotIn('response_format',requests[0])

    def test_invalid_request_fails_before_inference(self):
        for request in ({'messages':[]},{'messages':[{'role':'user','content':'input'}],'max_tokens':0},
                        {'messages':[{'role':'user','content':'input'}],'max_tokens':100000}):
            with self.assertRaises(ValueError):complete(request)


if __name__=='__main__':unittest.main()
