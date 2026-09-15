import copy
import base64
import io
import importlib.util
import json
import pathlib
import tempfile
import unittest
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('control', ROOT / 'osworld_control.py')
control = importlib.util.module_from_spec(spec)
spec.loader.exec_module(control)


class ContractTests(unittest.TestCase):
    def test_safe_aliases_and_fences(self):
        for kind in ['exec', 'EXEC', 'execute', 'click', 'type', 'plan']:
            a = control.canonical_action({'action': kind, 'command': "```python\nimport pyautogui\npyautogui.write('a;b')\npyautogui.press('enter')\n```"})
            self.assertEqual(a['action'], 'exec')
            self.assertIn("'a;b'", a['command'])
        self.assertEqual(control.canonical_action({'action': 'PLAN', 'plan': 'observe'})['action'], 'wait')
        self.assertEqual(control.canonical_action({'action': 'WAIT'})['action'], 'wait')

    def test_historical_malformed_commands(self):
        for command in ["pyautogui.click(380,238),[object Object]", "pyautogui.click(1,2),Wait for email", "pyautogui.click(1,2),#comment\npyautogui.press('enter')", "pyautogui.click(__import__('os').system('x'))", "pyautogui.write(open('x').read())", "pyautogui.sleep(999)", "pyautogui.scroll(-200)", "pyautogui.hotkey('ctrl','alt','t')"]:
            with self.subTest(command=command), self.assertRaises(ValueError):
                control.canonical_action({'action': 'exec', 'command': command})
        with self.assertRaises(ValueError):
            control.canonical_action({'action': 'exec', 'command': ['pyautogui.click(1,2)', {'explanation': 'x'}]})

    def test_literal_strings_are_not_code(self):
        a = control.canonical_action({'action':'exec','command':"pyautogui.write('open; requests; bash; shell')"})
        self.assertEqual(a['action'], 'exec')

    def test_verifier_counts_every_no_effect_action(self):
        v = control.Verifier()
        v.observe('entry\tSearch\t\t\t\t(1, 2)\t(20, 20)', '')
        for i in range(8):
            v.issued('pyautogui.click(%d,2)' % (i+1))
            result = v.observe('entry\tSearch\t\t\t\t(1, 2)\t(20, 20)', '')
            self.assertFalse(result['progress'])
        self.assertEqual(v.no_progress, 8)
        self.assertGreaterEqual(v.recovery_level, 3)

    def test_cyclic_screens_do_not_reset_recovery(self):
        v = control.Verifier()
        for i in range(16):
            v.observe('screen A' if i % 2 else 'screen B', '')
            v.issued('pyautogui.click(1,2)')
        self.assertGreater(v.no_progress, 10)

    def test_wait_observations_do_not_consume_no_progress_budget(self):
        v = control.Verifier()
        v.observe('same screen', '')
        for _ in range(20):
            v.observe('same screen', '')
        self.assertEqual(v.no_progress, 0)

    def test_new_observation_verifies_change(self):
        v = control.Verifier()
        v.observe('dialog closed', '')
        v.issued("pyautogui.press('enter')")
        self.assertTrue(v.observe('dialog opened', '')['progress'])

    def test_finish_requires_observed_change_and_evidence(self):
        v = control.Verifier()
        a={'action':'finish','confidence':0.95,'verification':'saved output','completed':True}
        v.observe('initial', '')
        self.assertFalse(v.can_finish(a, 'initial'))
        v.issued("pyautogui.press('enter')")
        v.observe('saved output', '')
        self.assertTrue(v.can_finish(a, 'saved output'))
        self.assertFalse(v.can_finish({**a,'verification':''}, 'saved output'))

    def test_long_instruction_preserves_objective_and_final_constraints(self):
        text='OBJECTIVE_START '+('middle '*2000)+' FINAL_CONSTRAINT_DO_NOT_SPEND'
        packed,_=control.pack_payload({'instruction':text,'observation':'','memory':'','screenshot_data_url':''})
        self.assertTrue(packed['instruction'].startswith('OBJECTIVE_START'))
        self.assertTrue(packed['instruction'].endswith('FINAL_CONSTRAINT_DO_NOT_SPEND'))
        self.assertIn('middle omitted',packed['instruction'])
        self.assertLessEqual(len(packed['instruction']),7000)

    def test_payload_gate_measures_utf8_bytes(self):
        body={'instruction':'task','observation':'雪'*60000,'memory':'m'*20000,'screenshot_data_url':''}
        packed, metrics=control.pack_payload(body)
        self.assertLessEqual(len(json.dumps(packed,ensure_ascii=False).encode()),control.MAX_PAYLOAD_BYTES)
        self.assertLessEqual(len(packed['observation']),control.MAX_TREE_CHARS)
        self.assertGreater(metrics['before_bytes'],metrics['after_bytes'])

    def test_visual_memory_is_separate_and_bounded(self):
        buf=io.BytesIO(); Image.new('RGB',(12,12),(255,255,255)).save(buf,format='PNG')
        tiny='data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
        packed,metrics=control.pack_payload({'instruction':'match visual style','observation':'menu\tGIMP\t\t\t\t(10, 0)\t(80, 20)',
            'memory':'','screenshot_data_url':tiny,'reference_screenshot_data_url':tiny})
        self.assertTrue(packed['screenshot_data_url'].startswith('data:image/jpeg;base64,'))
        self.assertTrue(packed['reference_screenshot_data_url'].startswith('data:image/jpeg;base64,'))
        self.assertLessEqual(metrics.get('reference_image_bytes',0),52000)
        self.assertLessEqual(len(json.dumps(packed).encode()),control.MAX_PAYLOAD_BYTES)

    def test_foreground_removes_recorded_occluded_controls(self):
        tree='label\tHome\tHome\t\t\t(1833, 1037)\t(40, 17)\nlabel\tfile.pdf\tfile.pdf\t\t\t(1793, 920)\t(120, 34)\npush-button\tCalendar (Ctrl+3)\t\t\t\t(77, 124)\t(30, 30)\npush-button\tMinimise\tMinimise\t\t\t(1802, 27)\t(30, 35)\nmenu\tGoogle Chrome\t\t\t\t(99, 0)\t(162, 27)'
        focused,active=control.foreground_context(tree)
        self.assertEqual(active,'Google Chrome')
        self.assertNotIn('(1833, 1037)',focused)
        self.assertNotIn('(77, 124)',focused)
        self.assertIn('file.pdf',focused)
        self.assertIn('BACKGROUND',focused)

    def test_pointer_without_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'POINTER_TARGET_REQUIRED'):
            control.ground_action({'action':'exec','command':"pyautogui.click(10, 20)"},'GIMP','',[])
        with self.assertRaisesRegex(ValueError,'POINTER_TARGET_INVALID'):
            control.ground_action({'action':'exec','command':"pyautogui.click(10, 20)",'target':{'source':'screenshot','label':''}},'GIMP','',[])

    def test_single_pointer_without_target_is_repaired_from_unique_accessibility_intent(self):
        obs="push-button\tConvert\t\t\t\t(1100, 660)\t(80, 52)"
        action={'action':'exec','plan':'Click Convert to continue','summary':'Use the visible Convert button',
                'command':"pyautogui.click(824, 646)"}
        out=control.ground_action(action,'GIMP',obs,[])
        self.assertEqual(out['target'],{'source':'accessibility','label':'Convert','role':'push-button'})
        self.assertEqual(out['command'],'pyautogui.click(1140, 686)')

    def test_missing_target_repair_fails_closed_for_multiple_pointer_calls(self):
        obs="push-button\tConvert\t\t\t\t(1100, 660)\t(80, 52)"
        action={'action':'exec','plan':'Click Convert','command':"pyautogui.click(824,646)\npyautogui.click(824,646)"}
        with self.assertRaisesRegex(ValueError,'POINTER_TARGET_REQUIRED'):
            control.ground_action(action,'GIMP',obs,[])

    def test_missing_target_repair_fails_closed_for_ambiguous_accessibility(self):
        obs=("push-button\tConvert\t\t\t\t(1100, 660)\t(80, 52)\n"
             "push-button\tConvert\t\t\t\t(900, 600)\t(80, 52)")
        action={'action':'exec','plan':'Click Convert','command':"pyautogui.click(824,646)"}
        with self.assertRaisesRegex(ValueError,'POINTER_TARGET_REQUIRED'):
            control.ground_action(action,'GIMP',obs,[])

    def test_accessibility_target_rewrites_wrong_click_coordinate(self):
        obs="push-button\tConvert\t\t\t\t(1100, 660)\t(80, 52)"
        action={'action':'exec','plan':'Click Convert to continue','summary':'Use the visible Convert button',
                'target':{'source':'accessibility','label':'Convert','role':'push-button'},
                'command':"pyautogui.click(824, 646)"}
        out=control.ground_action(action,'GIMP',obs,[])
        self.assertEqual(out['command'],'pyautogui.click(1140, 686)')
        self.assertIn('Accessibility-grounded',out.get('compiler_note',''))

    def test_accessibility_target_keeps_valid_coordinate(self):
        obs="push-button\tConvert\t\t\t\t(1100, 660)\t(80, 52)"
        action={'action':'exec','plan':'Click Convert','summary':'Convert image',
                'target':{'source':'accessibility','label':'Convert','role':'push-button'},
                'command':"pyautogui.click(1135, 680)"}
        out=control.ground_action(action,'GIMP',obs,[])
        self.assertEqual(out['command'],'pyautogui.click(1135, 680)')

    def test_rgb_verifier_detects_chroma_only_change(self):
        def data(color):
            buf=io.BytesIO(); Image.new('RGB',(96,64),color).save(buf,format='PNG')
            return 'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
        v=control.Verifier(); v.observe('same tree',data((224,32,32)))
        v.issued("pyautogui.press('enter')")
        self.assertTrue(v.observe('same tree',data((32,112,224)))['progress'])

    def test_background_accessibility_target_cannot_resolve(self):
        raw=('push-button\tConvert\t\t\t\t(1100, 660)\t(80, 52)\n'
             'push-button\tMinimise\t\t\t\t(1802, 27)\t(30, 35)\n'
             'menu\tGoogle Chrome\t\t\t\t(99, 0)\t(162, 27)')
        focused,app=control.foreground_context(raw)
        self.assertEqual(app,'Google Chrome'); self.assertNotIn('Convert',focused)
        action={'action':'exec','target':{'source':'accessibility','label':'Convert','role':'push-button'},
                'command':"pyautogui.click(824, 646)"}
        with self.assertRaisesRegex(ValueError,'ACCESSIBILITY_TARGET_UNRESOLVED'):
            control.ground_action(action,app,focused,[])

    def test_screenshot_target_is_not_rewritten_without_accessibility_proof(self):
        obs="push-button\tOther\t\t\t\t(1100, 660)\t(80, 52)"
        action={'action':'exec','plan':'Click visual swatch','summary':'Use screenshot target',
                'target':{'source':'screenshot','label':'swatch','role':''},
                'command':"pyautogui.click(824, 646)"}
        out=control.ground_action(action,'GIMP',obs,[])
        self.assertEqual(out['command'],'pyautogui.click(824, 646)')

    def test_declared_accessibility_target_must_resolve_uniquely(self):
        obs="push-button\tConvert\t\t\t\t(1100, 660)\t(80, 52)"
        missing={'action':'exec','target':{'source':'accessibility','label':'Save','role':'push-button'},'command':"pyautogui.click(10, 10)"}
        with self.assertRaisesRegex(ValueError,'ACCESSIBILITY_TARGET_UNRESOLVED'):
            control.ground_action(missing,'GIMP',obs,[])
        duplicate=obs+"\npush-button\tConvert\t\t\t\t(900, 600)\t(80, 52)"
        action={'action':'exec','target':{'source':'accessibility','label':'Convert','role':'push-button'},'command':"pyautogui.click(10, 10)"}
        with self.assertRaisesRegex(ValueError,'ACCESSIBILITY_TARGET_UNRESOLVED'):
            control.ground_action(action,'GIMP',duplicate,[])

    def test_explicit_screenshot_target_never_uses_plan_text_to_hijack_accessibility(self):
        obs="push-button\tConvert\t\t\t\t(1100, 660)\t(80, 52)"
        action={'action':'exec','plan':'Convert image after clicking visual swatch','summary':'Convert later',
                'target':{'source':'screenshot','label':'swatch','role':''},'command':"pyautogui.click(300, 400)"}
        out=control.ground_action(action,'GIMP',obs,[])
        self.assertEqual(out['command'],'pyautogui.click(300, 400)')

    def test_real_replay_desktop_plan_compiles_to_correct_shortcut(self):
        a=control.ground_action({'action':'exec','plan':'Bring the Desktop to the foreground to access files','command':"pyautogui.hotkey('alt', 'tab')"},'Google Chrome')
        self.assertEqual(a['command'],"pyautogui.hotkey('ctrl', 'win', 'd')")
        a=control.ground_action({'action':'exec','plan':'Bring Thunderbird to the foreground','command':"pyautogui.hotkey('alt', 'tab')"},'Google Chrome')
        self.assertEqual(a['command'],"pyautogui.hotkey('alt', 'tab')")

    def test_archive_title_is_not_filtered_as_desktop_file(self):
        raw='label\tfilter.zip\tfilter.zip\t\t\t(349, 216)\t(87, 17)\nlabel\tcity.zip\tcity.zip\t\t\t(1800, 800)\t(100, 20)\nmenu\tArchive Manager\t\t\t\t(99, 0)\t(150, 27)\nmenu\tSystem\t\t\t\t(1800, 0)\t(100, 27)\ndocument-presentation\tbackground slides'
        focused,app=control.foreground_context(raw)
        self.assertIn('(349, 216)',focused);self.assertNotIn('(1800, 800)',focused)
        self.assertNotIn('background slides',focused)

    def test_open_archive_cannot_abandon_context_without_verified_source_milestone(self):
        action={'action':'exec','plan':'show desktop files','command':"pyautogui.hotkey('ctrl', 'win', 'd')"}
        with self.assertRaisesRegex(ValueError,'OPEN_ARCHIVE_CONTEXT_SWITCH_FORBIDDEN'):
            control.ground_action(action,'Archive Manager','label\tfilter.zip',[])
        allowed=control.ground_action(action,'Archive Manager','label\tfilter.zip',[{'name':'archive source read complete','application':'Archive Manager','visible_text':'filter.zip'}])
        self.assertEqual(allowed['command'],"pyautogui.hotkey('ctrl', 'win', 'd')")

    def test_endpoint_and_cost_fail_closed(self):
        for data in [{'ok':True}, {'ok':True,'pipeline':'wrong','agent_build':'b','mandatory_cost_usd':0,'paid_fallback_used':False}]:
            with self.assertRaises(ValueError): control.validate_response(data,'p','b')


if __name__ == '__main__':
    unittest.main()
