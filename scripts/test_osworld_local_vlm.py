import base64
import os
import unittest
from unittest.mock import patch
from osworld_local_vlm import LocalVLMRoute, parse_action_object, MODEL_REVISION, _smol_chat_messages, _binary_contract

PNG=base64.b64encode(b'fixture').decode()
OBS='''Given the screenshot and info from accessibility tree as below:\ntag\tname\ttext\tclass\tdescription\tposition (top-left x&y)\tsize (w&h)\npush-button\tCompose\tCompose\t\t\t(86, 194)\t(157, 56)\npush-button\tClose\tClose\t\t\t(1882, 27)\t(38, 35)\nlink\tInbox 1\tInbox1\t\t\t(70, 274)\t(240, 32)\n'''
BODY={'instruction':'Dismiss visible menu','screenshot_data_url':'data:image/png;base64,'+PNG,'observation':OBS}
RAW=[{'role':'user','content':[{'type':'text','text':'Answer NO'},
      {'type':'image_url','image_url':{'url':'data:image/png;base64,'+PNG}}]}]


class LocalGroundingGateTests(unittest.TestCase):
    def test_local_pointer_requires_accessibility_target(self):
        with self.assertRaisesRegex(ValueError, 'LOCAL_GROUNDING_REQUIRED'):
            parse_action_object('{"action":"exec","command":"pyautogui.click(10, 20)"}',OBS)

    def test_local_accessibility_pointer_is_regrounded(self):
        action=parse_action_object('{"action":"exec","command":"pyautogui.click(10, 20)","target":{"source":"accessibility","label":"Compose","role":"push-button"}}',OBS)
        self.assertEqual(action['target']['label'],'Compose')
        self.assertEqual(action['command'],'pyautogui.click(164, 222)')

    def test_natural_language_click_is_compiled_from_accessibility(self):
        action=parse_action_object('Click the Compose button.',OBS)
        self.assertEqual(action['command'],'pyautogui.click(164, 222)')
        self.assertEqual(action['target']['source'],'accessibility')

    def test_natural_language_keyboard_is_compiled(self):
        action=parse_action_object('Press Ctrl+S to save.',OBS)
        self.assertEqual(action['command'],"pyautogui.hotkey('ctrl', 's')")

    def test_selector_candidates_include_visible_section_text(self):
        obs=OBS+'section\\t\\tH2 Rebaseline Directive: Operating Committee Pack\\t\\t\\t(626, 299)\\t(976, 20)\\n'
        from osworld_local_vlm import _selector_candidates
        items=_selector_candidates({'instruction':'Read the COO H2 Rebaseline Directive email','observation':obs,'active_application':'WPS Presentation'})
        matches=[x for x in items if x['action'].get('target',{}).get('label')=='H2 Rebaseline Directive: Operating Committee Pack']
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0]['action']['target']['role'],'section')

    def test_selector_candidates_are_bounded(self):
        from osworld_local_vlm import _selector_candidates, _SELECTOR_SYMBOLS
        obs='\\n'.join(f'push-button\\tButton {i}\\tButton {i}\\t\\t\\t({i*10}, 10)\\t(8, 8)' for i in range(80))
        items=_selector_candidates({'instruction':'choose button','observation':obs})
        self.assertLessEqual(len(items),len(_SELECTOR_SYMBOLS))

    def test_narrative_recovery_ignores_static_reference_and_uses_actionable_target(self):
        obs=OBS+'static\\tH2 Rebaseline Directive: Operating Committee Pack\\tH2 Rebaseline Directive: Operating Committee Pack\\t\\t\\t(400, 250)\\t(800, 60)\\n'
        raw=('The next step is to review H2 Rebaseline Directive: Operating Committee Pack and then click Compose. '
             'The next step is to click Compose.')
        action=parse_action_object(raw,obs)
        self.assertEqual(action['command'],'pyautogui.click(164, 222)')
        self.assertEqual(action['target']['role'],'push-button')
        self.assertEqual(action['target']['label'],'Compose')

    def test_narrative_recovery_static_only_stays_fail_closed_for_repair(self):
        obs=OBS+'static\\tH2 Rebaseline Directive: Operating Committee Pack\\tH2 Rebaseline Directive: Operating Committee Pack\\t\\t\\t(400, 250)\\t(800, 60)\\n'
        raw=('The next step is H2 Rebaseline Directive: Operating Committee Pack. '
             'The next step is H2 Rebaseline Directive: Operating Committee Pack.')
        with self.assertRaisesRegex(ValueError,'LOCAL_ACTION_REQUIRED'):
            parse_action_object(raw,obs)

    def test_unsafe_output_is_rejected_before_repair(self):
        with self.assertRaisesRegex(ValueError,'LOCAL_UNSAFE_OUTPUT_REJECTED'):
            parse_action_object("Use __import__('os').system('id')",OBS)

class LocalVLMTests(unittest.TestCase):
    def test_smol_template_folds_system_into_user_without_dropping_image(self):
        messages=[{'role':'system','content':[{'type':'text','text':'Return exactly YES or NO.'}]},
                  {'role':'user','content':[{'type':'text','text':'Is this a desktop?'},{'type':'image'}]}]
        folded=_smol_chat_messages(messages)
        self.assertEqual([m['role'] for m in folded],['user'])
        self.assertIn('Return exactly YES or NO.',folded[0]['content'][0]['text'])
        self.assertEqual([x['type'] for x in folded[0]['content'][1:]],['text','image'])

    def test_binary_contract_detects_explicit_yes_no_only(self):
        binary=[{'role':'user','content':[{'type':'text','text':'Answer only YES or NO.'},{'type':'image'}]}]
        open_ended=[{'role':'user','content':[{'type':'text','text':'Describe the image.'},{'type':'image'}]}]
        self.assertTrue(_binary_contract(binary))
        self.assertFalse(_binary_contract(open_ended))

    def test_model_revision_is_immutable_commit(self):
        self.assertRegex(MODEL_REVISION,r'^[0-9a-f]{40}$')

    def setUp(self):
        self.env=patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','ARBM_ENABLE_LOCAL_VLM':'1','ARBM_LOCAL_VLM_REPAIRS':'2'})
        self.env.start();self.addCleanup(self.env.stop)

    def test_binary_raw_messages(self):
        route=LocalVLMRoute(lambda text,image,tokens:'NO')
        result,attempts=route.call({},raw_messages=RAW,raw_tokens=10)
        self.assertEqual(result['text'],'NO')
        self.assertEqual(result['provider'],'local-cloud-vlm')
        self.assertTrue(attempts[-1]['zero_spend_confirmed'])

    def test_raw_messages_preserve_roles_order_and_all_images(self):
        seen=[]; png2=base64.b64encode(b'fixture-two').decode()
        raw=[{'role':'system','content':'Judge exactly.'},{'role':'user','content':[{'type':'text','text':'First'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+PNG}},{'type':'text','text':'Second'},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+png2}}]}]
        result,attempts=LocalVLMRoute(lambda messages,images,tokens: seen.append((messages,images,tokens)) or 'NO').call({},raw_messages=raw,raw_tokens=11)
        self.assertEqual(result['text'],'NO'); self.assertEqual(attempts[-1]['status'],200)
        messages,images,tokens=seen[0]
        self.assertEqual([m['role'] for m in messages],['system','user'])
        self.assertEqual([x['type'] for x in messages[1]['content']],['text','image','text','image'])
        self.assertEqual(images,[PNG,png2]); self.assertEqual(tokens,11)

    def test_raw_remote_image_fails_closed(self):
        called=[]; raw=[{'role':'user','content':[{'type':'image_url','image_url':{'url':'https://example.invalid/a.png'}}]}]
        result,attempts=LocalVLMRoute(lambda *args: called.append(args) or 'NO').call({},raw_messages=raw)
        self.assertIsNone(result); self.assertFalse(called)
        self.assertEqual(attempts[-1]['contract_error'],'LOCAL_INLINE_IMAGE_REQUIRED')

    def test_desktop_mode_keeps_single_image_contract(self):
        seen=[]; route=LocalVLMRoute(lambda text,image,tokens: seen.append((text,image,tokens)) or "pyautogui.press('enter')")
        result,_=route.call(BODY)
        self.assertEqual(result['action']['command'],"pyautogui.press('enter')")
        self.assertIsInstance(seen[0][0],str); self.assertIsInstance(seen[0][1],str)

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
            'Press Enter now.',
        ):
            with self.subTest(output=output):
                result,attempts=LocalVLMRoute(lambda *args:output).call(BODY)
                self.assertEqual(result['action']['command'],"pyautogui.press('enter')")
                self.assertEqual(attempts[-1]['status'],200)
        result,attempts=LocalVLMRoute(lambda *args:"__import__('os').system('id')").call(BODY)
        self.assertIsNone(result)
        self.assertEqual(attempts[-1]['contract_error'],'LOCAL_UNSAFE_OUTPUT_REJECTED')

    def test_contract_failure_gets_bounded_repair(self):
        outputs=iter(['I cannot format this action.','Press Enter.'])
        route=LocalVLMRoute(lambda *args:next(outputs))
        result,attempts=route.call(BODY,budget=100)
        self.assertEqual(result['action']['command'],"pyautogui.press('enter')")
        self.assertTrue(any(a.get('status')=='local_contract_retry' for a in attempts))
        self.assertEqual(attempts[-1]['status'],200)
        self.assertEqual(attempts[-1]['repair_index'],1)

    def test_pointer_repair_can_ground_visible_label(self):
        outputs=iter(['I should click something.','Click Compose.'])
        route=LocalVLMRoute(lambda *args:next(outputs))
        result,attempts=route.call(BODY,budget=100)
        self.assertEqual(result['action']['command'],'pyautogui.click(164, 222)')
        self.assertEqual(result['action']['target']['label'],'Compose')
        self.assertEqual(attempts[-1]['status'],200)

    def test_local_action_budget_and_compact_prompt(self):
        seen=[]
        route=LocalVLMRoute(lambda text,image,tokens: seen.append((text,tokens)) or "pyautogui.press('enter')")
        result,_=route.call({**BODY,'observation':OBS+'\n'+'x'*9000,'active_application':'GIMP'})
        self.assertEqual(result['action']['command'],"pyautogui.press('enter')")
        self.assertEqual(seen[0][1],96)
        self.assertLess(len(seen[0][0]),6000)


if __name__=='__main__':unittest.main()
