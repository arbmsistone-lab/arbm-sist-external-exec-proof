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

    def test_blank_libreoffice_impress_is_not_wps(self):
        body = snapshot('Untitled 1 - LibreOffice Impress', 'soffice.Soffice')
        with self.assertRaisesRegex(ValueError, 'UNAPPROVED'):
            preflight("pyautogui.press('enter')", body)

    def test_unrelated_browser_tab_rejected(self):
        body = snapshot('Unrelated search - Google Chrome', 'google-chrome')
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
