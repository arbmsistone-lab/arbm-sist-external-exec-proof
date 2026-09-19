"""Synthetic negative/positive contract tests; never an official task score."""
import copy
import hashlib
import json
import io
from PIL import Image
import tempfile
import unittest
from pathlib import Path
from arbm091.score_tracker import exact_result, scan_fatal
from arbm091.trace_gate import DECK, WORKBOOK, classify, digest, preflight, postflight, verify_trace
from arbm091 import wps_observer
import osworld_free_mesh_shim as shim
from unittest.mock import patch

SHA = 'a' * 40


def snapshot(title=DECK + ' - WPS Presentation', klass='wpp WPS', pid=40):
    return {'stable': True, 'captured_monotonic_ns': 10,
            'screen': [0, 0, 1920, 1080],
            'window': {'id': 5, 'pid': pid, 'title': title, 'owner_title': '',
                       'wm_class': klass, 'bbox': [100, 100, 1200, 800]},
            'hit_owner_id': 5,
            'target': {'pid': pid, 'label': 'Text box', 'role': 'entry',
                       'bbox': [200, 200, 300, 100], 'showing': True, 'enabled': True,
                       'application': 'wps'}}


class ScoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, value in {'candidate-sha.txt': SHA, 'task-id.txt': '091', 'task-rc.txt': '0'}.items():
            (self.root / name).write_text(value)
        self.result = self.root / 'results/task/091/result.txt'
        self.result.parent.mkdir(parents=True)
        self.result.write_text('1.0')
        self.summary = self.root / 'results/summary/results.json'
        self.summary.parent.mkdir(parents=True)
        self.summary.write_text('[{"task_id":"091","status":"success","score":1.0}]')

    def test_exact_one_matches(self):
        self.assertEqual(exact_result(self.root, SHA)['score'], '1.0')

    def test_less_than_one_rejected(self):
        for value in ('0', '0.999', '0.9999999999999999999999999999999'):
            with self.subTest(value=value):
                self.result.write_text(value)
                with self.assertRaisesRegex(ValueError, 'NOT_EXACTLY_ONE'):
                    exact_result(self.root, SHA)

    def test_non_finite_rejected(self):
        for value in ('NaN', 'Infinity', '-Infinity'):
            self.result.write_text(value)
            with self.assertRaises(ValueError):
                exact_result(self.root, SHA)

    def test_missing_result_rejected(self):
        self.result.unlink()
        with self.assertRaisesRegex(ValueError, 'RESULT_COUNT'):
            exact_result(self.root, SHA)

    def test_duplicate_result_rejected(self):
        other = self.root / 'results/second/091/result.txt'
        other.parent.mkdir(parents=True)
        other.write_text('1.0')
        with self.assertRaisesRegex(ValueError, 'RESULT_COUNT'):
            exact_result(self.root, SHA)

    def test_wrong_candidate_rejected(self):
        with self.assertRaisesRegex(ValueError, 'SHA_MISMATCH'):
            exact_result(self.root, 'b' * 40)

    def test_process_timeout_rejected(self):
        (self.root / 'task-rc.txt').write_text('124')
        with self.assertRaisesRegex(ValueError, 'PROCESS_FAILED'):
            exact_result(self.root, SHA)

    def test_summary_success_with_zero_is_not_success(self):
        self.summary.write_text('[{"task_id":"091","status":"success","score":0.0}]')
        with self.assertRaisesRegex(ValueError, 'SUMMARY_SCORE'):
            exact_result(self.root, SHA)

    def test_boolean_score_is_not_one(self):
        self.summary.write_text('[{"task_id":"091","status":"success","score":true}]')
        with self.assertRaisesRegex(ValueError, 'SUMMARY_SCORE'):
            exact_result(self.root, SHA)

    def test_fatal_timeout_overrides_one(self):
        (self.root / 'shim.jsonl').write_text('{"status":"TERMINAL_FAIL","reason":"NO_PROGRESS_TIMEOUT"}\n')
        with self.assertRaisesRegex(ValueError, 'FATAL_SHIM:NO_PROGRESS_TIMEOUT'):
            scan_fatal(self.root, final=True)

    def test_truncated_final_shim_rejected(self):
        (self.root / 'shim.jsonl').write_text('{"status":')
        with self.assertRaisesRegex(ValueError, 'TRUNCATED'):
            scan_fatal(self.root, final=True)


class ForegroundTests(unittest.TestCase):
    def test_wps_pointer_verified(self):
        self.assertEqual(preflight('pyautogui.click(250, 220)', snapshot()), 'wps-content')

    def test_reference_memo_allowed_but_not_wps(self):
        body = snapshot('MailHub - Google Chrome', 'google-chrome Google-chrome')
        self.assertEqual(preflight('pyautogui.click(250, 220)', body), 'reference')

    def test_reference_workbook_allowed_but_not_wps(self):
        body = snapshot(WORKBOOK + ' - WPS Spreadsheets', 'et WPS')
        self.assertEqual(preflight("pyautogui.press('down')", body), 'reference')

    def test_source_workbook_in_calc_is_a_legitimate_reference(self):
        body = snapshot(WORKBOOK + ' - LibreOffice Calc', 'soffice.Soffice')
        self.assertEqual(preflight("pyautogui.press('down')", body), 'reference')

    def test_exact_wps_bootstrap_root_allows_only_nondestructive_wait_or_escape(self):
        body = snapshot('WPS Office', 'wpsoffice wpsoffice', pid=3019)
        body['window']['owner_title'] = ''
        body['window']['bbox'] = [70, 27, 1850, 1053]
        body['target'] = None
        body['deck_file'] = {}
        body['deck_slide_text'] = {}
        body['deck_slide_shapes'] = {}
        self.assertEqual(classify(body['window']), 'wps-transient')
        self.assertEqual(preflight('pyautogui.sleep(0.2)', body), 'wps-transient')
        self.assertEqual(preflight("pyautogui.press('esc')", body), 'wps-transient')
        with self.assertRaisesRegex(ValueError, 'DEFAULT_OFFICE_ACTION_FORBIDDEN'):
            preflight("pyautogui.press('enter')", body)

    def test_wps_bootstrap_root_requires_exact_class_and_geometry(self):
        body = snapshot('WPS Office', 'wpsoffice wpsoffice', pid=3019)
        body['window']['owner_title'] = ''
        body['window']['bbox'] = [70, 27, 1850, 1053]
        body['target'] = None
        wrong_box = copy.deepcopy(body)
        wrong_box['window']['bbox'] = [71, 27, 1849, 1053]
        with self.assertRaisesRegex(ValueError, 'UNAPPROVED_APPLICATION'):
            preflight('pyautogui.sleep(0.2)', wrong_box)
        wrong_class = copy.deepcopy(body)
        wrong_class['window']['wm_class'] = 'chrome chrome'
        with self.assertRaisesRegex(ValueError, 'UNAPPROVED_APPLICATION'):
            preflight('pyautogui.sleep(0.2)', wrong_class)

    def test_blank_libreoffice_impress_is_not_wps(self):
        body = snapshot('Untitled 1 - LibreOffice Impress', 'soffice.Soffice')
        with self.assertRaisesRegex(ValueError, 'UNAPPROVED'):
            preflight("pyautogui.press('enter')", body)

    def test_unrelated_browser_tab_rejected(self):
        body = snapshot('Unrelated search - Google Chrome', 'google-chrome')
        with self.assertRaisesRegex(ValueError, 'UNAPPROVED'):
            preflight("pyautogui.press('enter')", body)

    def test_neutral_wait_is_allowed_before_approved_app(self):
        body = snapshot('Desktop', 'gnome-shell')
        self.assertEqual(preflight("pyautogui.sleep(0.2)", body), 'neutral-wait')

    def test_neutral_wait_is_bounded_and_cannot_authorize_interaction(self):
        body = snapshot('Desktop', 'gnome-shell')
        with self.assertRaisesRegex(ValueError, 'UNBOUNDED'):
            preflight("pyautogui.sleep(2.1)", body)
        with self.assertRaisesRegex(ValueError, 'UNAPPROVED'):
            preflight("pyautogui.press('enter')", body)

    def test_background_pid_rejected(self):
        body = snapshot()
        body['target']['pid'] = 999
        with self.assertRaisesRegex(ValueError, 'PID_MISMATCH'):
            preflight('pyautogui.click(250, 220)', body)

    def test_occluded_window_rejected(self):
        body = snapshot()
        body['hit_owner_id'] = 999
        with self.assertRaisesRegex(ValueError, 'OCCLUDED'):
            preflight('pyautogui.click(250, 220)', body)

    def test_coordinate_outside_box_rejected(self):
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_TARGET'):
            preflight('pyautogui.click(1500, 1000)', snapshot())

    def test_no_invented_click_without_target(self):
        body = snapshot()
        body['target'] = None
        with self.assertRaisesRegex(ValueError, 'UI_TARGET_UNAVAILABLE'):
            preflight('pyautogui.click(250, 220)', body)

    def test_unstable_foreground_rejected(self):
        body = snapshot()
        body['stable'] = False
        with self.assertRaisesRegex(ValueError, 'UNSTABLE'):
            preflight("pyautogui.press('enter')", body)

    def test_missing_pid_rejected(self):
        body = snapshot()
        body['window']['pid'] = 0
        with self.assertRaisesRegex(ValueError, 'PID_UNPROVEN'):
            preflight("pyautogui.press('enter')", body)

    def test_task091_canonical_spatial_fallback_requires_target_deck_proof(self):
        body = snapshot(DECK + ' - WPS Office', 'wpsoffice wpsoffice', pid=2594)
        body['window']['bbox'] = [70, 27, 1850, 1053]
        body['screen'] = [0, 0, 1920, 1080]
        body['target'] = None
        body['active_slide'] = 1
        body['deck_slide_text'] = {'1':'Growth Plan Draft'}
        body['deck_slide_shapes'] = {'1':[{
            'id':6,'name':'CoverTitle','text':'Growth Plan Draft',
            'geometry':{'x':749808,'y':1078992,'w':5852160,'h':1234440}}]}
        body['deck_file'] = {'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                             'sha256':'a'*64,'size':1234,'mtime_ns':1,
                             'slide_size':{'w':12192000,'h':6858000}}
        self.assertEqual(preflight('pyautogui.doubleClick(745, 335, interval=0.08)', body), 'wps-content')
        self.assertEqual(preflight('pyautogui.click(869, 391)', body), 'wps-content')

        no_proof = copy.deepcopy(body)
        no_proof['deck_slide_text'] = {}
        with self.assertRaisesRegex(ValueError, 'UI_TARGET_UNAVAILABLE'):
            preflight('pyautogui.doubleClick(869, 391, interval=0.08)', no_proof)

        off_shape = copy.deepcopy(body)
        with self.assertRaisesRegex(ValueError, 'SHAPE_POINT_UNPROVEN'):
            preflight('pyautogui.doubleClick(1215, 470, interval=0.08)', off_shape)

        missing_shape = copy.deepcopy(body)
        missing_shape['deck_slide_shapes'] = {}
        with self.assertRaisesRegex(ValueError, 'SHAPE_POINT_UNPROVEN'):
            preflight('pyautogui.doubleClick(869, 391, interval=0.08)', missing_shape)

        wrong_geometry = copy.deepcopy(body)
        wrong_geometry['window']['bbox'] = [71, 27, 1849, 1053]
        with self.assertRaisesRegex(ValueError, 'CANONICAL_DECK_GEOMETRY_UNPROVEN'):
            preflight('pyautogui.doubleClick(869, 391, interval=0.08)', wrong_geometry)

        wrong_screen = copy.deepcopy(body)
        wrong_screen['screen'] = [0, 0, 1919, 1080]
        with self.assertRaisesRegex(ValueError, 'CANONICAL_SCREEN_UNPROVEN'):
            preflight('pyautogui.doubleClick(869, 391, interval=0.08)', wrong_screen)

        missing_digest = copy.deepcopy(body)
        missing_digest['deck_file']['sha256'] = ''
        with self.assertRaisesRegex(ValueError, 'TARGET_DECK_FILE_UNPROVEN'):
            preflight('pyautogui.doubleClick(869, 391, interval=0.08)', missing_digest)

        missing_slide_size = copy.deepcopy(body)
        missing_slide_size['deck_file'].pop('slide_size', None)
        with self.assertRaisesRegex(ValueError, 'SHAPE_POINT_UNPROVEN'):
            preflight('pyautogui.doubleClick(869, 391, interval=0.08)', missing_slide_size)

    def test_task091_spatial_proof_is_scoped_to_observed_active_slide(self):
        body = snapshot(DECK + ' - WPS Office', 'wpsoffice wpsoffice', pid=2594)
        body['window']['bbox'] = [70, 27, 1850, 1053]
        body['screen'] = [0, 0, 1920, 1080]
        body['target'] = None
        body['active_slide'] = 1
        body['deck_slide_text'] = {'1':'Planning posture','2':'Other slide'}
        shared = {'id':7,'name':'CoverSub','text':'Planning posture',
                  'geometry':{'x':768096,'y':2743200,'w':5669280,'h':1280160}}
        body['deck_slide_shapes'] = {'1':[copy.deepcopy(shared)], '2':[copy.deepcopy(shared)]}
        body['deck_file'] = {'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                             'sha256':'a'*64,'slide_size':{'w':12192000,'h':6858000}}
        self.assertEqual(preflight('pyautogui.doubleClick(738, 516, interval=0.08)', body), 'wps-content')
        missing = copy.deepcopy(body)
        missing.pop('active_slide')
        with self.assertRaisesRegex(ValueError, 'ACTIVE_SLIDE_UNPROVEN'):
            preflight('pyautogui.doubleClick(738, 516, interval=0.08)', missing)
        wrong = copy.deepcopy(body)
        wrong['active_slide'] = 3
        with self.assertRaisesRegex(ValueError, 'ACTIVE_SLIDE_SHAPES_UNPROVEN'):
            preflight('pyautogui.doubleClick(738, 516, interval=0.08)', wrong)

    def test_task091_text_hitpoint_must_belong_to_exactly_one_shape(self):
        body = snapshot(DECK + ' - WPS Office', 'wpsoffice wpsoffice', pid=2594)
        body['window']['bbox'] = [70, 27, 1850, 1053]
        body['screen'] = [0, 0, 1920, 1080]
        body['target'] = None
        body['active_slide'] = 1
        body['deck_slide_text'] = {'1':'A B'}
        body['deck_slide_shapes'] = {'1':[
            {'id':1,'name':'A','text':'A','geometry':{'x':749808,'y':1078992,'w':5852160,'h':1234440}},
            {'id':2,'name':'B','text':'B','geometry':{'x':749808,'y':1078992,'w':5852160,'h':1234440}},
        ]}
        body['deck_file'] = {'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                             'sha256':'a'*64,'slide_size':{'w':12192000,'h':6858000}}
        with self.assertRaisesRegex(ValueError, 'SHAPE_POINT_UNPROVEN'):
            preflight('pyautogui.doubleClick(745, 335, interval=0.08)', body)

    def test_application_switch_is_not_edit(self):
        self.assertEqual(preflight("pyautogui.hotkey('alt', 'tab')", snapshot()), 'application-switch')

    def test_wps_2019_launcher_is_controlled_application_switch(self):
        body = snapshot()
        body['target'] = {'pid': 1136, 'label': 'WPS 2019', 'role': 'push button',
                          'bbox': [0, 852, 70, 64], 'showing': True, 'enabled': True,
                          'application': 'gnome-shell'}
        body['hit_owner_id'] = 41943043
        self.assertEqual(preflight('pyautogui.click(35, 884)', body), 'application-switch')

    def test_non_wps_gnome_launcher_still_rejected(self):
        body = snapshot()
        body['target'] = {'pid': 1136, 'label': 'VLC media player', 'role': 'push button',
                          'bbox': [0, 237, 70, 64], 'showing': True, 'enabled': True,
                          'application': 'gnome-shell'}
        body['hit_owner_id'] = 41943043
        with self.assertRaisesRegex(ValueError, 'PID_MISMATCH'):
            preflight('pyautogui.click(35, 269)', body)

    def test_wrong_deck_rejected(self):
        body = snapshot('Other.pptx - WPS Presentation', 'wpp WPS')
        with self.assertRaisesRegex(ValueError, 'UNAPPROVED'):
            preflight("pyautogui.write('text')", body)

    def test_native_wps_replace_modal_is_wps_content(self):
        body = snapshot('Presentation', 'wpp wpp', pid=2684)
        body['window']['owner_title'] = 'Replace'
        self.assertEqual(classify(body['window']), 'wps-presentation')
        self.assertEqual(preflight("pyautogui.write('$40.9M')", body), 'wps-content')

    def test_native_wps_find_modal_is_wps_content(self):
        body = snapshot('Find', 'wpp wpp', pid=2684)
        body['window']['owner_title'] = 'Presentation'
        self.assertEqual(preflight("pyautogui.press('tab')", body), 'wps-content')

    def test_foreign_or_generic_wpp_window_is_still_rejected(self):
        body = snapshot('Calculator', 'wpp wpp', pid=2684)
        body['window']['owner_title'] = 'Utility'
        with self.assertRaisesRegex(ValueError, 'UNAPPROVED'):
            preflight("pyautogui.press('enter')", body)

    def test_system_check_is_authorized_transient_with_tab_space_and_verified_click(self):
        body = snapshot('System Check', 'wpp wpp', pid=2689)
        body['window']['owner_title'] = DECK + ' - WPS Office'
        self.assertEqual(classify(body['window']), 'wps-transient')
        self.assertEqual(preflight("pyautogui.press('tab')", body), 'wps-transient')
        self.assertEqual(preflight("pyautogui.press('space')", body), 'wps-transient')
        click = copy.deepcopy(body)
        click['target'] = {'pid':2689,'label':'Close','role':'push button',
                           'bbox':[650,360,90,32],'showing':True,'enabled':True,
                           'application':'wps'}
        click['window']['bbox']=[120,112,699,327]
        click['hit_owner_id']=click['window']['id']
        self.assertEqual(preflight("pyautogui.click(695, 376)", click), 'wps-transient')
        with self.assertRaisesRegex(ValueError, 'TRANSIENT'):
            preflight("pyautogui.hotkey('alt', 'tab')", body)
        with self.assertRaisesRegex(ValueError, 'TRANSIENT'):
            preflight("pyautogui.hotkey('alt', 'f4')", body)

    def test_system_check_postflight_requires_same_wps_pid_and_real_close(self):
        before = snapshot('System Check', 'wpp wpp', pid=2689)
        before['window']['owner_title'] = DECK + ' - WPS Office'
        after_tab = copy.deepcopy(before)
        after_tab['captured_monotonic_ns'] = 11
        self.assertEqual(postflight("pyautogui.press('tab')", before, after_tab), 'wps-transient')
        after_space = copy.deepcopy(before)
        after_space['captured_monotonic_ns'] = 12
        self.assertEqual(postflight("pyautogui.press('space')", before, after_space), 'wps-transient')
        after_deck = snapshot(DECK + ' - WPS Office', 'wpp wpp', pid=2689)
        after_deck['captured_monotonic_ns'] = 13
        self.assertEqual(postflight("pyautogui.click(695, 376)", before, after_deck), 'wps-presentation')
        drift = snapshot(WORKBOOK + ' - WPS Spreadsheets', 'et WPS', pid=2566)
        drift['captured_monotonic_ns'] = 14
        with self.assertRaisesRegex(ValueError, 'WPS_TRANSIENT_CLOSE_UNPROVEN'):
            postflight("pyautogui.click(695, 376)", before, drift)

    def test_system_check_click_requires_real_close_target(self):
        body = snapshot('System Check', 'wpp wpp', pid=2689)
        body['window']['owner_title'] = DECK + ' - WPS Office'
        body['window']['bbox'] = [120,112,699,327]
        body['hit_owner_id'] = body['window']['id']
        body['target'] = {'pid':2689,'label':'Other','role':'push button',
                          'bbox':[650,360,90,32],'showing':True,'enabled':True,
                          'application':'wps'}
        with self.assertRaisesRegex(ValueError, 'CLOSE_TARGET_UNPROVEN'):
            preflight("pyautogui.click(695, 376)", body)

    def test_system_check_space_allows_proven_owner_handoff_across_pid(self):
        before = snapshot('System Check', 'wpp wpp', pid=2719)
        before['window']['owner_title'] = DECK + ' - WPS Office'
        after = snapshot(DECK + ' - WPS Office', 'wpsoffice wpsoffice', pid=2594)
        self.assertEqual(postflight("pyautogui.press('space')", before, after), 'wps-presentation')

    def test_system_check_space_rejects_cross_pid_non_owner_drift(self):
        before = snapshot('System Check', 'wpp wpp', pid=2719)
        before['window']['owner_title'] = DECK + ' - WPS Office'
        drift = snapshot(WORKBOOK + ' - WPS Spreadsheets', 'et WPS', pid=2594)
        with self.assertRaisesRegex(ValueError, 'OWNER_HANDOFF_UNPROVEN|CLOSE_UNPROVEN'):
            postflight("pyautogui.press('space')", before, drift)

    def test_non_transient_deck_does_not_authorize_destructive_modal_close(self):
        body = snapshot(DECK + ' - WPS Presentation', 'wpp WPS', pid=2689)
        self.assertEqual(classify(body['window']), 'wps-presentation')
        self.assertEqual(preflight("pyautogui.press('enter')", body), 'wps-content')


class ObserverStabilityTests(unittest.TestCase):
    def test_transient_unstable_probe_retries_until_stable(self):
        samples=[
            ({'stable':False,'window':{'pid':2684,'wm_class':'wpp wpp'}},b'a'),
            ({'stable':True,'window':{'pid':2684,'wm_class':'wpp wpp'}},b'b'),
        ]
        with patch.object(wps_observer,'_probe_once',side_effect=samples),              patch.object(wps_observer.time,'sleep',lambda *_:None):
            payload,png=wps_observer._settled_probe(object(),None,attempts=3,delay=0)
        self.assertTrue(payload['stable'])
        self.assertEqual(png,b'b')

    def test_persistently_unstable_probe_stays_fail_closed(self):
        samples=[
            ({'stable':False,'window':{'pid':2684,'wm_class':'wpp wpp'}},b'a'),
            ({'stable':False,'window':{'pid':2684,'wm_class':'wpp wpp'}},b'b'),
            ({'stable':False,'window':{'pid':2684,'wm_class':'wpp wpp'}},b'c'),
        ]
        with patch.object(wps_observer,'_probe_once',side_effect=samples),              patch.object(wps_observer.time,'sleep',lambda *_:None),              self.assertRaisesRegex(ValueError,'FOREGROUND_UNSTABLE'):
            wps_observer._settled_probe(object(),None,attempts=3,delay=0)

class TraceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.rows = []

    def store_snapshot(self, name, value, image_tag):
        meta = json.dumps(value).encode()
        # Generated test images, not production/official benchmark evidence.
        output = io.BytesIO()
        Image.new('RGB', (1920, 1080), (0, 0, 0) if image_tag == 'before' else (1, 1, 1)).save(output, format='PNG')
        png = output.getvalue()
        (self.root / (name + '.json')).write_bytes(meta)
        (self.root / (name + '.png')).write_bytes(png)
        return {'metadata': name + '.json', 'metadata_sha256': hashlib.sha256(meta).hexdigest(),
                'screenshot': name + '.png', 'screenshot_sha256': hashlib.sha256(png).hexdigest()}

    def add(self, command, app=None):
        ordinal = len(self.rows) + 1
        before = copy.deepcopy(app or snapshot())
        after = copy.deepcopy(before)
        before['captured_monotonic_ns'] = ordinal * 10
        after['captured_monotonic_ns'] = ordinal * 10 + 1
        row = {'ordinal': ordinal, 'previous_sha256': self.rows[-1]['event_sha256'] if self.rows else '0' * 64,
               'candidate_sha': SHA, 'task_id': '091', 'run_id': '10', 'run_attempt': '1',
               'step': ordinal, 'substep': 1, 'kind': 'action', 'status': 'executed', 'returncode': 0,
               'command': command, 'source_command': command,
               'command_sha256': hashlib.sha256(command.encode()).hexdigest(),
               'before': self.store_snapshot(str(ordinal) + '-before', before, 'before'),
               'after': self.store_snapshot(str(ordinal) + '-after', after, 'after'),
               'scope': preflight(command, before)}
        row['event_sha256'] = digest(row)
        self.rows.append(row)
        (self.root / 'wps-trace.jsonl').write_text(''.join(json.dumps(value) + '\n' for value in self.rows))

    def test_trace_requires_wps_effect_and_save(self):
        self.add("pyautogui.write('updated text')")
        self.add("pyautogui.hotkey('ctrl', 's')")
        verdict = verify_trace(self.root, SHA, '10', '1')
        self.assertEqual(verdict['agent_save_actions'], 1)

    def test_chrome_only_does_not_certify_wps(self):
        self.add("pyautogui.press('down')", snapshot('MailHub', 'google-chrome'))
        with self.assertRaisesRegex(ValueError, 'WPS_ACTIONS_UNPROVEN'):
            verify_trace(self.root, SHA, '10', '1')

    def test_no_save_rejected(self):
        self.add("pyautogui.write('updated text')")
        with self.assertRaisesRegex(ValueError, 'SAVE_UNPROVEN'):
            verify_trace(self.root, SHA, '10', '1')

    def test_tamper_rejected(self):
        self.add("pyautogui.write('updated text')")
        self.rows[0]['command'] = "pyautogui.write('tampered')"
        (self.root / 'wps-trace.jsonl').write_text(json.dumps(self.rows[0]) + '\n')
        with self.assertRaisesRegex(ValueError, 'TRACE_CHAIN_INVALID'):
            verify_trace(self.root, SHA, '10', '1')

    def test_wrong_run_rejected(self):
        self.add("pyautogui.write('updated text')")
        with self.assertRaisesRegex(ValueError, 'PROVENANCE_MISMATCH'):
            verify_trace(self.root, SHA, '11', '1')

    def test_missing_trace_rejected(self):
        with self.assertRaisesRegex(ValueError, 'WPS_TRACE_MISSING'):
            verify_trace(self.root, SHA, '10', '1')


if __name__ == '__main__':
    unittest.main()


class Task091CompactEditTests(unittest.TestCase):
    def test_text_mode_is_pointer_established_not_f2_injected(self):
        samples=[
            ('$42.8M', '$40.9M'),
            ('214', '206'),
            ('GTM', 'Data Migration'),
            ('Planning posture: accelerate growth through H2 scale-up',
             'Planning posture: stabilize and recover with disciplined sequencing'),
            ('Growth Plan Draft',
             'H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'),
        ]
        for old,new in samples:
            self.assertFalse(shim._task091_needs_explicit_text_mode(old,new))
            command=shim._task091_write_command(new, ensure_text_mode=False)
            self.assertEqual(command.splitlines()[0], "pyautogui.hotkey('ctrl', 'a')")
            self.assertNotIn("pyautogui.press('f2')", command)
            with self.assertRaisesRegex(ValueError, 'TASK091_TEXT_MODE_MUST_BE_POINTER_ESTABLISHED'):
                shim._task091_write_command(new, ensure_text_mode=True)


    def test_guest_probe_keeps_signed_table_cell_extraction_contract(self):
        source=Path('scripts/arbm091/guest_probe.py').read_text(encoding='utf-8')
        compile(source, 'guest_probe.py', 'exec')
        self.assertIn("graphicFrame", source)
        self.assertIn("tblGrid", source)
        self.assertIn("'kind':'table-cell'", source)
        for token in ("gridSpan", "rowSpan", "hMerge", "vMerge"):
            self.assertIn(token, source)
        self.assertIn("grid_index += grid_span", source)

    def test_all_task091_spatial_replacements_use_bounded_post_hit_writer(self):
        checked=0
        for _slide,_x,_y,old,new in shim.TASK091_SPATIAL_TEXT_EDITS:
            if shim._task091_norm(old)==shim._task091_norm(new):
                continue
            checked += 1
            self.assertFalse(shim._task091_needs_explicit_text_mode(old,new), (old,new))
            command=shim._task091_write_command(new, ensure_text_mode=False)
            self.assertEqual(command.splitlines()[0], "pyautogui.hotkey('ctrl', 'a')")
            self.assertNotIn("press('f2')", command)
            self.assertLessEqual(len(command.splitlines()), 7)
        self.assertGreaterEqual(checked, 70)

    def test_empty_replacement_is_not_authorized_as_text_mode(self):
        self.assertFalse(shim._task091_needs_explicit_text_mode('', 'x'))
        self.assertFalse(shim._task091_needs_explicit_text_mode('x', ''))


