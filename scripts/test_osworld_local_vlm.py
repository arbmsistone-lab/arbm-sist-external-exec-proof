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

    def test_action_output_accepts_safe_model_wrappers(self):
        valid='{"action":"exec","command":"pyautogui.press(\'enter\')"}'
        for output in (
            valid,
            '```json\n'+valid+'\n```',
            'I will dismiss the dialog.\n'+valid+'\nThis is the visible action.',
            "```python\nimport pyautogui\npyautogui.press('enter')\n```",
            "pyautogui.press('enter')",
            '{"command":"pyautogui.press(\'enter\')"}',
        ):
            with self.subTest(output=output):
                result,attempts=LocalVLMRoute(lambda *args:output).call(BODY)
                self.assertEqual(result['action']['command'],"pyautogui.press('enter')")
                self.assertEqual(attempts[-1]['status'],200)
        for output,error in (
            ("```python\n__import__('os').system('id')\n```",'LOCAL_ACTION_REQUIRED'),
            ('{"action":"exec","command":','LOCAL_ACTION_REQUIRED'),
        ):
            with self.subTest(output=output):
                result,attempts=LocalVLMRoute(lambda *args:output).call(BODY)
                self.assertIsNone(result)
                self.assertEqual(attempts[-1]['status'],'local_model_error')
                self.assertEqual(attempts[-1]['contract_error'],error)

    def test_local_action_budget_and_compact_prompt(self):
        seen=[]
        route=LocalVLMRoute(lambda text,image,tokens: seen.append((text,tokens)) or "pyautogui.press('enter')")
        result,_=route.call({**BODY,'observation':'x'*9000,'active_application':'GIMP'})
        self.assertEqual(result['action']['command'],"pyautogui.press('enter')")
        self.assertEqual(seen[0][1],96)
        self.assertLess(len(seen[0][0]),6000)


if __name__=='__main__':unittest.main()
