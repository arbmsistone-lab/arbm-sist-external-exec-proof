import base64
import os
import unittest
from unittest.mock import patch
from osworld_local_vlm import LocalVLMRoute

PNG=base64.b64encode(b'fixture').decode()
BODY={'instruction':'Dismiss visible menu','screenshot_data_url':'data:image/png;base64,'+PNG}
RAW=[{'role':'user','content':[{'type':'text','text':'Answer NO'},
      {'type':'image_url','image_url':{'url':'data:image/png;base64,'+PNG}}]}]


class LocalVLMTests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','ARBM_ENABLE_LOCAL_VLM':'1'})
        self.env.start();self.addCleanup(self.env.stop)

    def test_binary_raw_messages(self):
        route=LocalVLMRoute(lambda text,image,tokens:'NO')
        result,attempts=route.call({},raw_messages=RAW,raw_tokens=10)
        self.assertEqual(result['text'],'NO')
        self.assertEqual(result['provider'],'local-cloud-vlm')
        self.assertTrue(attempts[-1]['zero_spend_confirmed'])

    def test_disabled_never_runs_model(self):
        with patch.dict(os.environ,{'ARBM_ENABLE_LOCAL_VLM':'0'}):
            result,attempts=LocalVLMRoute(lambda *x: (_ for _ in ()).throw(Exception())).call(BODY)
        self.assertIsNone(result);self.assertEqual(attempts[-1]['status'],'disabled')


if __name__=='__main__':unittest.main()
