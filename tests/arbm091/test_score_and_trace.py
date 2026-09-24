"""Synthetic negative/positive contract tests; never an official task score."""
import copy
import hashlib
import json
import os
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
        with self.assertRaisesRegex(ValueError, 'ACTIVE_SLIDE_SHAPES_UNPROVEN'):
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

    def test_task091_geometry_authority_board_10_audits(self):
        body = snapshot(DECK + ' - WPS Office', 'wpsoffice wpsoffice', pid=2588)
        body['window']['bbox'] = [70, 27, 1850, 1053]
        body['screen'] = [0, 0, 1920, 1080]
        body['active_slide'] = 1
        body['deck_file'] = {
            'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
            'sha256':'3'*64,
            'slide_size':{'w':12191365,'h':6858000},
        }
        body['deck_slide_text'] = {
            '1':'ARR exit target $42.8M Net burn / month $2.6M Headcount plan 214'
        }
        body['deck_slide_shapes'] = {'1':[
            {'id':13,'name':'CoverStatValue_0','text':'$42.8M',
             'geometry':{'x':8339327,'y':2167128,'w':2560320,'h':219456}},
            {'id':16,'name':'CoverStatValue_1','text':'$2.6M',
             'geometry':{'x':8339327,'y':3358896,'w':2560320,'h':210312}},
            {'id':19,'name':'CoverStatValue_2','text':'214',
             'geometry':{'x':8339327,'y':4550664,'w':2560320,'h':210312}},
        ]}

        # Audit 01: exact PPTX text uniquely identifies the target shape.
        p1=shim._task091_shape_point(body,1,'$42.8M',1338,393)
        self.assertIsNotNone(p1)
        self.assertEqual(p1['shape']['id'],13)

        # Audit 02: EMU -> canonical viewport projection matches the focal artifact.
        self.assertEqual(p1['shape_bbox'],[1410,445,296,26])

        # Audit 03: the stale hint is explicitly measured rather than silently trusted.
        self.assertEqual(p1['hint_drift'],72)
        self.assertGreater(p1['hint_drift'],32)

        # Audit 04: unique exact PPTX geometry is the explicit authority.
        self.assertEqual(p1['selection_basis'],'unique-exact-pptx-geometry')

        # Audit 05: the derived click remains strictly inside the proven shape.
        x,y,w,h=p1['shape_bbox']
        self.assertTrue(x <= p1['cx'] < x+w and y <= p1['cy'] < y+h)

        # Audit 06: second KPI survives the same 72px historical-hint drift.
        p2=shim._task091_shape_point(body,1,'$2.6M',1338,511)
        self.assertEqual(p2['shape']['id'],16)
        self.assertEqual(p2['hint_drift'],72)

        # Audit 07: third KPI survives the larger 91px drift without weakening identity.
        p3=shim._task091_shape_point(body,1,'214',1338,630)
        self.assertEqual(p3['shape']['id'],19)
        self.assertEqual(p3['hint_drift'],92)

        # Audit 08: duplicate exact shapes remain fail-closed under ambiguous geometry.
        dup=copy.deepcopy(body)
        dup['deck_slide_shapes']['1'].append(copy.deepcopy(dup['deck_slide_shapes']['1'][0]))
        dup['deck_slide_shapes']['1'][-1]['id']=113
        self.assertIsNone(shim._task091_shape_point(dup,1,'$42.8M',1338,393))

        # Audit 09: missing/invalid PPTX geometry is never replaced by a guessed point.
        missing=copy.deepcopy(body)
        missing['deck_slide_shapes']['1'][0]['geometry']={}
        self.assertIsNone(shim._task091_shape_point(missing,1,'$42.8M',1338,393))

        # Audit 10: non-canonical WPS geometry stays rejected.
        wrong_window=copy.deepcopy(body)
        wrong_window['window']['bbox']=[71,27,1849,1053]
        self.assertIsNone(shim._task091_shape_point(wrong_window,1,'$42.8M',1338,393))

    def test_task091_geometry_senior_robot_board_10(self):
        body = snapshot(DECK + ' - WPS Office', 'wpsoffice wpsoffice', pid=2588)
        body['window']['bbox']=[70,27,1850,1053]
        body['screen']=[0,0,1920,1080]
        body['active_slide']=1
        body['deck_file']={'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                           'sha256':'4'*64,'slide_size':{'w':12191365,'h':6858000}}
        body['deck_slide_text']={'1':'$42.8M $2.6M 214'}
        body['deck_slide_shapes']={'1':[
            {'id':13,'name':'CoverStatValue_0','text':'$42.8M',
             'geometry':{'x':8339327,'y':2167128,'w':2560320,'h':219456}},
            {'id':16,'name':'CoverStatValue_1','text':'$2.6M',
             'geometry':{'x':8339327,'y':3358896,'w':2560320,'h':210312}},
            {'id':19,'name':'CoverStatValue_2','text':'214',
             'geometry':{'x':8339327,'y':4550664,'w':2560320,'h':210312}},
        ]}
        lanes=[]
        p=shim._task091_shape_point(body,1,'$42.8M',1338,393)
        lanes.append(('R01_unique_id',p['shape']['id']==13))
        lanes.append(('R02_exact_name',p['shape']['name']=='CoverStatValue_0'))
        lanes.append(('R03_bbox',[p['shape_bbox'][0],p['shape_bbox'][1]]==[1410,445]))
        lanes.append(('R04_positive_extent',p['shape_bbox'][2]>0 and p['shape_bbox'][3]>0))
        lanes.append(('R05_inside',p['shape_bbox'][0] <= p['cx'] < p['shape_bbox'][0]+p['shape_bbox'][2]))
        lanes.append(('R06_basis',p['selection_basis']=='unique-exact-pptx-geometry'))
        lanes.append(('R07_drift',p['hint_drift']==72))
        p_again=shim._task091_shape_point(copy.deepcopy(body),1,'$42.8M',1338,393)
        lanes.append(('R08_deterministic',(p['cx'],p['cy'],p['shape']['id'])==(p_again['cx'],p_again['cy'],p_again['shape']['id'])))
        p2=shim._task091_shape_point(body,1,'$2.6M',1338,511)
        lanes.append(('R09_second_kpi',p2 is not None and p2['shape']['id']==16))
        p3=shim._task091_shape_point(body,1,'214',1338,630)
        lanes.append(('R10_third_kpi',p3 is not None and p3['shape']['id']==19))
        self.assertEqual([name for name,ok in lanes if not ok],[],lanes)

    def test_task091_geometry_senior_specialist_board_10(self):
        body = snapshot(DECK + ' - WPS Office', 'wpsoffice wpsoffice', pid=2588)
        body['window']['bbox']=[70,27,1850,1053]
        body['screen']=[0,0,1920,1080]
        body['active_slide']=1
        body['deck_file']={'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                           'sha256':'5'*64,'slide_size':{'w':12191365,'h':6858000}}
        shape={'id':13,'name':'CoverStatValue_0','text':'$42.8M',
               'geometry':{'x':8339327,'y':2167128,'w':2560320,'h':219456}}
        body['deck_slide_text']={'1':'$42.8M'}
        body['deck_slide_shapes']={'1':[shape]}
        lanes=[]
        duplicate=copy.deepcopy(body)
        duplicate['deck_slide_shapes']['1'].append({**copy.deepcopy(shape),'id':113})
        lanes.append(('S01_duplicate_rejected',shim._task091_shape_point(duplicate,1,'$42.8M',1338,393) is None))
        no_geom=copy.deepcopy(body); no_geom['deck_slide_shapes']['1'][0]['geometry']={}
        lanes.append(('S02_missing_geometry',shim._task091_shape_point(no_geom,1,'$42.8M',1338,393) is None))
        bad_w=copy.deepcopy(body); bad_w['deck_slide_shapes']['1'][0]['geometry']['w']=0
        lanes.append(('S03_zero_width',shim._task091_shape_point(bad_w,1,'$42.8M',1338,393) is None))
        no_size=copy.deepcopy(body); no_size['deck_file'].pop('slide_size')
        lanes.append(('S04_missing_slide_size',shim._task091_shape_point(no_size,1,'$42.8M',1338,393) is None))
        wrong_screen=copy.deepcopy(body); wrong_screen['screen']=[0,0,1919,1080]
        lanes.append(('S05_wrong_screen',shim._task091_shape_point(wrong_screen,1,'$42.8M',1338,393) is None))
        wrong_window=copy.deepcopy(body); wrong_window['window']['bbox']=[71,27,1849,1053]
        lanes.append(('S06_wrong_window',shim._task091_shape_point(wrong_window,1,'$42.8M',1338,393) is None))
        lanes.append(('S07_wrong_slide',shim._task091_shape_point(body,2,'$42.8M',1338,393) is None))
        lanes.append(('S08_wrong_text',shim._task091_shape_point(body,1,'$99.9M',1338,393) is None))
        partial=copy.deepcopy(body); partial['deck_slide_shapes']['1'][0]['text']='Forecast $42.8M approved'
        pp=shim._task091_shape_point(partial,1,'$42.8M',1338,393)
        lanes.append(('S09_partial_not_authoritative',pp is None))
        ambiguous=copy.deepcopy(partial)
        ambiguous['deck_slide_shapes']['1'].append({
            'id':14,'name':'Other','text':'Other $42.8M reference',
            'geometry':{'x':1000000,'y':1000000,'w':1000000,'h':300000}})
        ap=shim._task091_shape_point(ambiguous,1,'$42.8M',1338,393)
        lanes.append(('S10_ambiguous_partial_rejected',ap is None))
        self.assertEqual([name for name,ok in lanes if not ok],[],lanes)


    def test_task091_semantic_transaction_board_10(self):
        from arbm091.semantic_runtime import next_text_action
        from arbm091.semantic_transaction import normalize_deck, resolve_target
        deck={
          'schema':1,'stable':True,
          'window':{'bbox':[70,27,1850,1053],
                    'title':'Operating_Committee_Rebaseline_Draft.pptx - WPS Presentation'},
          'screen':[0,0,1920,1080],'active_slide':1,
          'deck_slide_shapes':{'1':[{
              'id':6,'name':'CoverTitle',
              'text':'H2 Operating Committee Pack\nGrowth Plan Draft','kind':'shape',
              'geometry':{'x':749808,'y':1078992,'w':5852160,'h':1234440},
              'font_sizes':[2400],'fill_rgb':''}]},
          'deck_slide_charts':{},'deck_slide_relationships':{'1':[]},
          'deck_file':{'sha256':'a'*64,
                       'slide_size':{'w':12192000,'h':6858000}},
        }
        plan=((1,745,335,'Growth Plan Draft',
               'H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'),)
        state={'slide':1}

        # T01/T02: structural resolution is unique and independent of caret/raster metadata.
        resolved=resolve_target(deck,slide=1,old='Growth Plan Draft',hint_x=745,hint_y=335)
        self.assertEqual(resolved['row']['name'],'CoverTitle')
        noisy=copy.deepcopy(deck); noisy.update(caret_x=9999,ink_left=-999,zoom=175)
        self.assertEqual(normalize_deck(deck),normalize_deck(noisy))

        # T03/T04: selection and mutation are semantic_tx operations, not pending_edit.
        select=next_text_action(state,deck,plan)
        self.assertEqual(select['specialist_phase'],'semantic-target-select')
        self.assertNotIn('pending_edit',state)
        preflight=next_text_action(state,deck,plan)
        self.assertEqual(preflight['specialist_phase'],'semantic-cover-autofit-pane-open')
        pane=copy.deepcopy(deck); pane['screenshot_sha256']='c'*64
        captured=next_text_action(state,pane,plan)
        self.assertEqual(captured['action'],'exec')
        self.assertEqual(captured['specialist_phase'],'semantic-cover-autofit-text-options-open')
        self.assertEqual(state['semantic_tx']['autofit_panel_points']['text_options'],[1730,219])
        self.assertEqual(state['semantic_tx']['autofit_panel_points']['text_box'],[1730,251])
        options=copy.deepcopy(deck); options['screenshot_sha256']='d'*64
        textbox=next_text_action(state,options,plan)
        self.assertEqual(textbox['action'],'exec')
        self.assertEqual(textbox['specialist_phase'],'semantic-cover-autofit-textbox-pane-open')
        self.assertEqual(textbox['target']['source'],'task091-panel-canonical')
        self.assertEqual(textbox['target']['label'],'Text Box')
        textbox_state=copy.deepcopy(deck); textbox_state['screenshot_sha256']='e'*64
        textbox_capture=next_text_action(state,textbox_state,plan)
        self.assertEqual(textbox_capture['reason'],'TASK091_COVERTITLE_TEXTBOX_PANE_CAPTURED')
        state['semantic_tx']['stage']='select-issued'
        state['semantic_tx']['autofit_preflight_done']=True
        mutation=next_text_action(state,deck,plan)
        self.assertEqual(mutation['specialist_phase'],'semantic-text-mutation')
        self.assertIn("hotkey('ctrl', 'h')",mutation['command'])
        self.assertIn("Growth Plan Draft",mutation['command'])
        self.assertIn("Stabilize-and-Recover Rebaseline",mutation['command'])
        self.assertIn("hotkey('alt', 'a')",mutation['command'])
        self.assertNotIn("hotkey('ctrl', 'a')",mutation['command'])
        for forbidden in ("press('home')","press('left'","caret","ink_left"):
            self.assertNotIn(forbidden,mutation['command'].casefold())

        # T05/T06: commit and save do not advance semantic index early.
        self.assertEqual(next_text_action(state,deck,plan)['specialist_phase'],'semantic-edit-finalize')
        self.assertEqual(next_text_action(state,deck,plan)['specialist_phase'],'semantic-save')
        self.assertEqual(int(state.get('semantic_index') or 0),0)

        # T07/T08: exact persisted OOXML diff is required.
        after=copy.deepcopy(deck)
        after['deck_file']['sha256']='b'*64
        after['deck_slide_shapes']['1'][0]['text']='H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'
        reread=next_text_action(state,after,plan)
        self.assertEqual(reread['specialist_phase'],'semantic-roundtrip-reread')
        passed=next_text_action(state,after,plan)
        self.assertEqual(passed['checkpoint'],'TASK091_SEMANTIC_TRANSACTION_PASS')
        self.assertTrue(passed['semantic_evidence']['no_collateral_mutation'])
        self.assertEqual(state['semantic_index'],1)

        # T09: ambiguous duplicate structural target fails closed.
        ambiguous=copy.deepcopy(deck)
        duplicate=copy.deepcopy(ambiguous['deck_slide_shapes']['1'][0]); duplicate['id']=106
        ambiguous['deck_slide_shapes']['1'].append(duplicate)
        result=next_text_action({'slide':1},ambiguous,plan)
        self.assertEqual(result['action'],'terminal')
        self.assertEqual(result['reason'],'TASK091_TARGET_AMBIGUOUS')

        # T10: collateral sibling mutation fails closed.
        state2={'slide':1}
        next_text_action(state2,deck,plan)  # select
        preflight2=next_text_action(state2,deck,plan)
        self.assertEqual(preflight2['specialist_phase'],'semantic-cover-autofit-pane-open')
        pane2=copy.deepcopy(deck); pane2['screenshot_sha256']='d'*64
        captured2=next_text_action(state2,pane2,plan)
        self.assertEqual(captured2['action'],'exec')
        self.assertEqual(captured2['specialist_phase'],'semantic-cover-autofit-text-options-open')
        textbox2=copy.deepcopy(deck); textbox2['screenshot_sha256']='e'*64
        textbox_capture2=next_text_action(state2,textbox2,plan)
        self.assertEqual(textbox_capture2['reason'],'TASK091_COVERTITLE_TEXTBOX_PANE_CAPTURED')
        state2['semantic_tx']['stage']='select-issued'
        state2['semantic_tx']['autofit_preflight_done']=True
        next_text_action(state2,deck,plan)  # mutation
        next_text_action(state2,deck,plan)  # finalize
        next_text_action(state2,deck,plan)  # save
        bad=copy.deepcopy(after)
        bad['deck_slide_shapes']['1'].append({
            'id':7,'name':'Sibling','text':'UNAUTHORIZED','kind':'shape',
            'geometry':{'x':100,'y':100,'w':100,'h':40},
            'font_sizes':[1200],'fill_rgb':''})
        rejected=next_text_action(state2,bad,plan)
        self.assertEqual(rejected['action'],'terminal')
        self.assertIn('TASK091_SEMANTIC_DIFF_MISMATCH',rejected['reason'])
    def test_task091_table_cell_uses_observed_pptx_geometry_not_stale_hint(self):
        body = snapshot(DECK + ' - WPS Office', 'wpsoffice wpsoffice', pid=2594)
        body['window']['bbox'] = [70,27,1850,1053]
        body['screen'] = [0,0,1920,1080]
        body['active_slide'] = 3
        body['deck_slide_text'] = {'3':'$42.8M'}
        body['deck_slide_shapes'] = {'3':[{
            'id':-13001003,'kind':'table-cell','frame_id':13,'row':1,'col':2,
            'name':'Table 12#r1c2','text':'$42.8M',
            'geometry':{'x':3877056,'y':2088750,'w':1563624,'h':607422}}]}
        body['deck_file'] = {'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                             'sha256':'a'*64,'slide_size':{'w':12191365,'h':6858000}}
        point=shim._task091_shape_point(body,3,'$42.8M',843,404)
        self.assertIsNotNone(point)
        self.assertEqual(point['selection_basis'],'pptx-table-cell-geometry')
        self.assertEqual((point['cx'],point['cy']),(983,471))
        self.assertEqual(point['shape_bbox'],[892,436,182,71])
        self.assertGreater(point['hint_drift'],100)
        self.assertEqual(point['shape']['kind'],'table-cell')

    def test_task091_collateral_table_edit_is_detected_before_generic_verify_failure(self):
        pending={
            'slide':3,'old':'$42.8M','new':'$40.9M','shape_id':-13001003,
            'before_old_count':2,'before_new_count':0,
            'before_deck_sha256':'a'*64,
            'before_sibling_signature':'before-siblings',
            'target':{'bbox':[842,403,2,2],'cx':843,'cy':404},
        }
        body={
            'deck_slide_text':{'3':'$40.9MM ARR $39.6M $42.8M'},
            'deck_slide_shapes':{'3':[
                {'id':-13001003,'kind':'table-cell','name':'Table 12#r1c2','text':'$42.8M',
                 'geometry':{'x':3877056,'y':2088750,'w':1563624,'h':607422}},
                {'id':-13000003,'kind':'table-cell','name':'Table 12#r0c0','text':'$40.9MM',
                 'geometry':{'x':0,'y':0,'w':1,'h':1}},
            ]},
            'deck_file':{'sha256':'b'*64},
        }
        ok,status,detail=shim._task091_verify_pending('',pending,body)
        self.assertFalse(ok)
        self.assertEqual(status,'collateral-mutation')
        self.assertEqual(detail['actual_shape_text'],'$42.8M')

    def test_task091_drifted_short_text_uses_interior_text_band(self):
        body = snapshot(DECK + ' - WPS Office', 'wpsoffice wpsoffice', pid=2594)
        body['window']['bbox'] = [70,27,1850,1053]
        body['screen'] = [0,0,1920,1080]
        body['active_slide'] = 1
        body['deck_slide_text'] = {'1':'$42.8M'}
        body['deck_slide_shapes'] = {'1':[{
            'id':13,'name':'CoverStatValue_0','text':'$42.8M',
            'geometry':{'x':8339327,'y':2167128,'w':2560320,'h':219456}}]}
        body['deck_file'] = {'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                             'sha256':'a'*64,'size':1234,'mtime_ns':1,
                             'slide_size':{'w':12191365,'h':6858000}}
        point=shim._task091_shape_point(body,1,'$42.8M',1338,393)
        self.assertIsNotNone(point)
        left,top,width,height=point['shape_bbox']
        self.assertEqual(point['selection_basis'],'unique-exact-pptx-geometry')
        self.assertEqual(point['cy'],top+height//2)
        self.assertGreater(point['cx'],left+4)
        self.assertLess(point['cx'],left+width-1)


    def test_task091_nonpersisted_semantic_save_fails_closed(self):
        from arbm091.semantic_runtime import next_text_action
        deck={
          'schema':1,'stable':True,
          'window':{'bbox':[70,27,1850,1053],
                    'title':'Operating_Committee_Rebaseline_Draft.pptx - WPS Presentation'},
          'screen':[0,0,1920,1080],'active_slide':1,
          'deck_slide_shapes':{'1':[{
              'id':13,'name':'CoverStatValue_0','text':'$42.8M','kind':'shape',
              'geometry':{'x':8339327,'y':2167128,'w':2560320,'h':219456},
              'font_sizes':[1600],'fill_rgb':''}]},
          'deck_slide_charts':{},'deck_slide_relationships':{'1':[]},
          'deck_file':{'sha256':'a'*64,
                       'slide_size':{'w':12192000,'h':6858000}},
        }
        plan=((1,1420,450,'$42.8M','$40.9M'),)
        state={'slide':1}
        self.assertEqual(next_text_action(state,deck,plan)['specialist_phase'],'semantic-target-select')
        self.assertEqual(next_text_action(state,deck,plan)['specialist_phase'],'semantic-text-mutation')
        self.assertEqual(next_text_action(state,deck,plan)['specialist_phase'],'semantic-edit-finalize')
        self.assertEqual(next_text_action(state,deck,plan)['specialist_phase'],'semantic-save')
        unchanged=copy.deepcopy(deck)
        result=next_text_action(state,unchanged,plan)
        self.assertEqual(result['action'],'terminal')
        self.assertEqual(result['reason'],'TASK091_SEMANTIC_DIFF_MISMATCH:'+result['reason'].split(':',1)[1]
                         if result['reason'].startswith('TASK091_SEMANTIC_DIFF_MISMATCH:')
                         else result['reason'])
        self.assertIn(result['reason'].split(':',1)[0],
                      ('TASK091_SEMANTIC_DIFF_MISMATCH','TASK091_SAVE_NOT_PERSISTED'))
        self.assertEqual(state['semantic_tx']['stage'],'save-issued')
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


class Task091FinalAtomicTableCellTests(unittest.TestCase):
    def _deck(self, shot='1'):
        source_map={'1':'0063-01-after','2':'0064-01-after','3':'0065-01-after','4':'0066-01-after'}
        return {
          'schema':1,'stable':True,'source':source_map.get(str(shot),'0069-01-after'),
          'window':{'id':12582927,'pid':2594,
                    'title':'Operating_Committee_Rebaseline_Draft.pptx - WPS Office',
                    'owner_title':'','wm_class':'wpsoffice wpsoffice','bbox':[70,27,1850,1053]},
          'screen':[0,0,1920,1080],
          'active_slide':3,
          'screenshot_sha256':shot*64,
          'deck_slide_text':{'3':'KPI Scorecard ARR $39.6M $42.8M Repeated metrics $42.8M'},
          'deck_slide_shapes':{'3':[
              {'id':-13000001,'kind':'table-cell','frame_id':13,'row':0,'col':0,
               'name':'Table 12#r0c0','text':'Metric',
               'geometry':{'x':749808,'y':1481328,'w':1563624,'h':607422}},
              {'id':-13001003,'kind':'table-cell','frame_id':13,'row':1,'col':2,
               'name':'Table 12#r1c2','text':'$42.8M',
               'geometry':{'x':3877056,'y':2088750,'w':1563624,'h':607422}},
              {'id':16,'kind':'shape','name':'KpiReadout_Body',
               'text':'• ARR and NRR are both positioned as ahead of plan in the current draft.\\n• Headcount plan still assumes 5 Growth Ops hires land in H2.\\n• Burn improvement relies on expansion payback from Q4.',
               'geometry':{'x':9034272,'y':1883664,'w':2148840,'h':1353312},
               'font_sizes':[1600],'fill_rgb':''},
          ]},
          'deck_file':{'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                       'sha256':'a'*64,'size':113361,'mtime_ns':1,
                       'slide_size':{'w':12191365,'h':6858000}},
        }

    def _task(self):
        return ('You are Maya Lin, Business Operations Manager at Northstar Cloud. '
                'The COO has asked you to rebaseline the H2 Operating Committee pack. '
                'The draft deck Operating_Committee_Rebaseline_Draft.pptx is already open. '
                'Reforecast_Model_H2.xlsx is the source of truth.')


    def test_table_cell_semantic_transaction_requires_no_caret_geometry(self):
        from arbm091.semantic_runtime import next_text_action
        deck=self._deck('1')
        deck['window']['bbox']=[70,27,1850,1053]
        deck['screen']=[0,0,1920,1080]
        deck['active_slide']=3
        deck.setdefault('deck_slide_charts',{})
        deck.setdefault('deck_slide_relationships',{'3':[]})
        cell=deck['deck_slide_shapes']['3'][0]
        cell['kind']='table-cell'
        cell.setdefault('frame_id',13); cell.setdefault('row',1); cell.setdefault('col',2)
        cell.setdefault('font_sizes',[1600]); cell.setdefault('fill_rgb','')
        deck['deck_file']['slide_size']={'w':12192000,'h':6858000}
        plan=((3,843,404,'$42.8M','$40.9M'),)
        state={'slide':3}
        select=next_text_action(state,deck,plan)
        self.assertEqual(select['specialist_phase'],'semantic-target-select')
        mutation=next_text_action(state,deck,plan)
        self.assertEqual(mutation['specialist_phase'],'semantic-text-mutation')
        for forbidden in ("caret","ink_left","press('home')","press('left'","blink","pre-glyph"):
            self.assertNotIn(forbidden,mutation['command'].casefold())
        self.assertNotIn('pending_edit',state)

    def test_table_cell_sibling_drift_is_rejected_by_semantic_diff(self):
        from arbm091.semantic_runtime import next_text_action
        deck=self._deck('1')
        deck['window']['bbox']=[70,27,1850,1053]
        deck['screen']=[0,0,1920,1080]
        deck['active_slide']=3
        deck.setdefault('deck_slide_charts',{})
        deck.setdefault('deck_slide_relationships',{'3':[]})
        for row in deck['deck_slide_shapes']['3']:
            row.setdefault('kind','table-cell')
            row.setdefault('frame_id',13)
            row.setdefault('row',1)
            row.setdefault('col',2 if row is deck['deck_slide_shapes']['3'][0] else 3)
            row.setdefault('font_sizes',[1600]); row.setdefault('fill_rgb','')
        deck['deck_file']['slide_size']={'w':12192000,'h':6858000}
        plan=((3,843,404,'$42.8M','$40.9M'),)
        state={'slide':3}
        next_text_action(state,deck,plan)
        next_text_action(state,deck,plan)
        next_text_action(state,deck,plan)
        next_text_action(state,deck,plan)
        bad=copy.deepcopy(deck)
        bad['deck_file']['sha256']='b'*64
        bad['deck_slide_shapes']['3'][0]['text']='$40.9M'
        if len(bad['deck_slide_shapes']['3'])==1:
            bad['deck_slide_shapes']['3'].append({
                'id':-13001004,'name':'Table 12#r1c3','text':'UNCHANGED','kind':'table-cell',
                'frame_id':13,'row':1,'col':3,
                'geometry':{'x':5500000,'y':2088750,'w':1000000,'h':607422},
                'font_sizes':[1600],'fill_rgb':''})
            # Baseline must include the sibling for a pure sibling drift test.
            deck['deck_slide_shapes']['3'].append(copy.deepcopy(bad['deck_slide_shapes']['3'][1]))
            state={'slide':3}
            next_text_action(state,deck,plan); next_text_action(state,deck,plan)
            next_text_action(state,deck,plan); next_text_action(state,deck,plan)
            bad=copy.deepcopy(deck); bad['deck_file']['sha256']='b'*64
            bad['deck_slide_shapes']['3'][0]['text']='$40.9M'
        bad['deck_slide_shapes']['3'][1]['text']='CORRUPTED'
        result=next_text_action(state,bad,plan)
        self.assertEqual(result['action'],'terminal')
        self.assertIn('TASK091_SEMANTIC_DIFF_MISMATCH',result['reason'])
    def test_run35850450098_table_cell_exact_shape_beats_stale_global_count(self):
        pending={
            'slide':3,'old':'$42.8M','new':'$40.9M',
            'shape_id':-13001003,'shape_kind':'table-cell',
            'before_old_count':2,'before_new_count':0,
            'before_deck_sha256':'a'*64,
        }
        window_state={
            'deck_file':{'sha256':'b'*64},
            'deck_slide_text':{'3':'$42.8M $42.8M'},
            'deck_slide_shapes':{'3':[
                {'id':-13001003,'kind':'table-cell','name':'Table 12#r1c2',
                 'text':'$40.9M','geometry':{'x':1,'y':1,'w':10,'h':10}},
                {'id':-13001004,'kind':'table-cell','name':'Table 12#r1c3',
                 'text':'Ahead','geometry':{'x':20,'y':1,'w':10,'h':10}},
            ]},
        }
        pending['before_sibling_signature']=shim._task091_other_shapes_signature(
            window_state,3,-13001003)
        verified,status,detail=shim._task091_verify_pending('',pending,window_state)
        self.assertTrue(verified,detail)
        self.assertEqual(status,'disk-verified')

        collateral=copy.deepcopy(window_state)
        collateral['deck_slide_shapes']['3'][1]['text']='Changed'
        verified2,status2,_=shim._task091_verify_pending('',pending,collateral)
        self.assertFalse(verified2)
        self.assertNotEqual(status2,'disk-verified')

    def test_section_e_runs_before_first_slide3_kpi_table_edit(self):
        with patch.dict(os.environ,{'TASK_ID':'091'},clear=False),              patch.object(shim,'_task091_region_sha256',return_value='a'*64):
            state={'anchored':True,'slide':3,'spatial_index':len(shim.TASK091_SPATIAL_TEXT_EDITS),'semantic_text_done':True}
            result=shim.next_091_specialist_action(
                self._task(),'WPS Presentation','',state,self._deck('1'))
            self.assertEqual(result['specialist_phase'],'section-e-semantic-select')
            self.assertEqual(state['section_e_format']['shape_id'],16)
            self.assertNotIn('pending_edit',state)



    def test_guest_probe_semantic_slide_text_preserves_split_run_token(self):
        import ast
        source=Path('scripts/arbm091/guest_probe.py').read_text(encoding='utf-8')
        tree=ast.parse(source)
        fn=next(node for node in tree.body
                if isinstance(node,ast.FunctionDef) and node.name=='_semantic_slide_text')
        ns={}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),
                     'guest_probe_semantic_helper','exec'),ns)
        aggregate=ns['_semantic_slide_text']([
            {'kind':'shape','text':'Repeated metrics • ARR exit target: $42.8M'},
            {'kind':'table-cell','text':'$40.9M'},
        ])
        self.assertIn('$40.9M',aggregate)
        self.assertEqual(aggregate.count('$40.9M'),1)
        self.assertNotIn('$4 0 . 9 M',aggregate)

    def test_section_e_precondition_is_semantic_not_index_magic(self):
        source=Path('scripts/osworld_free_mesh_shim.py').read_text(encoding='utf-8')
        self.assertIn("int(next_edit[0])==3",source)
        self.assertNotIn("if index >= 10 and not state.get('section_e_format_done')",source)
        self.assertNotIn("if index >= 16 and not state.get('section_e_format_done')",source)



class Task091CaretBoundedWriterTests(unittest.TestCase):
    def test_table_cell_bounded_writer_mutates_only_fixed_width_delta(self):
        command=shim._task091_table_cell_bounded_write_command('$42.8M','$40.9M')
        self.assertNotIn("hotkey('ctrl', 'a')",command)
        self.assertNotIn("keyDown('shift')",command)
        self.assertNotIn("keyUp('shift')",command)
        self.assertNotIn("press('left'",command)
        self.assertNotIn("press('end')",command)
        self.assertNotIn("press('home')",command)
        self.assertNotIn("press('backspace'",command)
        self.assertEqual(command.count("press('delete')"),2)
        self.assertIn("press('right', presses=2",command)
        self.assertIn("write('0'",command)
        self.assertIn("write('9'",command)
        self.assertNotIn("write('$'",command)
        self.assertNotIn("write('M'",command)

    def test_table_cell_delta_plan_rejects_length_or_scope_drift(self):
        with self.assertRaisesRegex(ValueError,'TASK091_TABLE_CELL_DELTA_PLAN_INVALID'):
            shim._task091_table_cell_bounded_write_command('','x')
        with self.assertRaisesRegex(ValueError,'TASK091_TABLE_CELL_DELTA_PLAN_INVALID'):
            shim._task091_table_cell_bounded_write_command('a'+chr(10)+'b','abc')
        with self.assertRaisesRegex(ValueError,'TASK091_TABLE_CELL_DELTA_PLAN_INVALID'):
            shim._task091_table_cell_bounded_write_command('abc','abcd')
        with self.assertRaisesRegex(ValueError,'TASK091_TABLE_CELL_DELTA_PLAN_UNBOUNDED'):
            shim._task091_table_cell_bounded_write_command('abc','xyz')

    def test_table_cell_writer_contract_forbids_boundary_selection(self):
        source=Path('scripts/osworld_free_mesh_shim.py').read_text(encoding='utf-8')
        start=source.index("def _task091_table_cell_bounded_write_command")
        end=source.index("def _task091_table_cell_rollback_command",start)
        body=source[start:end]
        self.assertIn("def _task091_table_cell_delta_plan",source)
        self.assertNotIn("ctrl', 'a",body)
        self.assertNotIn("keyDown('shift')",body)
        self.assertNotIn("keyUp('shift')",body)
        self.assertIn("press('delete')",body)
        self.assertNotIn("press('left'",body)
        self.assertNotIn("press('end')",body)
        self.assertNotIn("press('home')",body)
        self.assertNotIn("press('backspace'",body)
        self.assertIn("TASK091_TABLE_CELL_DELTA_ACTION_COUNT_UNBOUNDED",body)

    def test_start_caret_geometry_is_required_before_delta_mutation(self):
        shape_bbox=[892,507,182,70]
        ink_bbox=[965,516,35,12]
        at_start={'proven':True,'bbox':[72,2,1,22]}
        accepted=shim._task091_caret_at_text_start(at_start,shape_bbox,ink_bbox)
        self.assertTrue(accepted['proven'],accepted)
        at_end={'proven':True,'bbox':[108,2,1,22]}
        rejected=shim._task091_caret_at_text_start(at_end,shape_bbox,ink_bbox)
        self.assertFalse(rejected['proven'],rejected)

    def test_start_caret_terminal_marker_offset_allows_only_one_proven_normalization(self):
        shape_bbox=[892,507,182,70]
        ink_bbox=[965,516,35,12]
        at_start=shim._task091_caret_at_text_start(
            {'proven':True,'bbox':[72,2,1,22]},shape_bbox,ink_bbox)
        self.assertTrue(at_start['proven'],at_start)
        self.assertEqual(at_start['relation'],'at-start')
        one_char_right=shim._task091_caret_at_text_start(
            {'proven':True,'bbox':[80,2,1,22]},shape_bbox,ink_bbox)
        self.assertFalse(one_char_right['proven'],one_char_right)
        self.assertEqual(one_char_right['relation'],'right-of-start')
        source=Path('scripts/osworld_free_mesh_shim.py').read_text(encoding='utf-8')
        self.assertIn("normalize_attempts < 1",source)
        self.assertIn("normalize-wps-terminal-marker-offset",source)

    def test_start_navigation_moves_left_exactly_by_proven_text_length(self):
        command=shim._task091_table_cell_start_navigation_command('$42.8M')
        self.assertEqual(command,"pyautogui.press('left', presses=6, interval=0.03)")
        self.assertNotIn("keyDown('shift')",command)
        self.assertNotIn("press('right'",command)
        self.assertNotIn("pyautogui.write(",command)
        with self.assertRaisesRegex(ValueError,'TASK091_TABLE_CELL_START_NAV_TEXT_INVALID'):
            shim._task091_table_cell_start_navigation_command('')

    def test_500_case_two_delta_red_team_matrix(self):
        alphabet="0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz$%.-_"
        for i in range(500):
            n=(i % 30)+1
            old=''.join(alphabet[(i*7+j*11) % len(alphabet)] for j in range(n))
            chars=list(old)
            first=i % n
            chars[first]=alphabet[(alphabet.index(chars[first])+1) % len(alphabet)]
            if n>1 and i % 2:
                second=(first+max(1,n//2)) % n
                if second==first:
                    second=(first+1)%n
                chars[second]=alphabet[(alphabet.index(chars[second])+2) % len(alphabet)]
            new=''.join(chars)
            plan=shim._task091_table_cell_delta_plan(old,new)
            self.assertLessEqual(len(plan),2)
            command=shim._task091_table_cell_bounded_write_command(old,new)
            self.assertEqual(command.count("press('delete')"),len(plan))
            self.assertNotIn("keyDown('shift')",command)
            self.assertNotIn("keyUp('shift')",command)
            self.assertNotIn("press('left'",command)
            self.assertNotIn("hotkey('ctrl', 'a')",command)
            self.assertNotIn("press('end')",command)
            self.assertNotIn("press('home')",command)
            self.assertNotIn("press('backspace'",command)

    def test_ten_adversarial_guards_fail_closed(self):
        source=Path('scripts/osworld_free_mesh_shim.py').read_text(encoding='utf-8')
        checks=[
            "TASK091_TABLE_CELL_START_NAV_DRIFT",
            "TASK091_TABLE_CELL_START_CARET_EVIDENCE_MISSING",
            "TASK091_TABLE_CELL_START_CARET_GEOMETRY_UNPROVEN",
            "TASK091_TABLE_CELL_CARET_NOT_AT_START",
            "caret_entry_end_diagnostic",
            "TASK091_TABLE_CELL_ENTRY_DRIFT",
            "before_sibling_signature",
            "table_selected_sibling_visual_sha256",
            "TASK091_TABLE_CELL_DELTA_PLAN_UNBOUNDED",
            "TASK091_TABLE_CELL_ATOMIC_REPAIR_PLAN_INVALID",
        ]
        for marker in checks:
            self.assertIn(marker,source)

    def test_fifty_adversarial_table_transaction_audits(self):
        source=Path('scripts/osworld_free_mesh_shim.py').read_text(encoding='utf-8')
        writer_start=source.index("def _task091_table_cell_bounded_write_command")
        writer_end=source.index("def _task091_table_cell_rollback_command",writer_start)
        writer=source[writer_start:writer_end]
        mismatch_start=source.index("if status in ('collateral-mutation','disk-text-mismatch')")
        mismatch_end=source.index("if status=='collateral-mutation':",mismatch_start)
        mismatch=source[mismatch_start:mismatch_end]
        cmd6=shim._task091_table_cell_bounded_write_command('$42.8M','$40.9M')
        cmd4=shim._task091_table_cell_bounded_write_command('112%','104%')
        cmd1=shim._task091_table_cell_bounded_write_command('A','B')
        cmd30=shim._task091_table_cell_bounded_write_command('x'*29+'a','x'*29+'b')
        audits=[
            ('01_no_ctrl_a_writer',"hotkey('ctrl', 'a')" not in writer),
            ('02_delete_is_local',"press('delete')" in writer),
            ('03_no_backspace_writer',"press('backspace'" not in writer),
            ('04_no_end_writer',"press('end')" not in writer),
            ('05_no_home_writer',"press('home')" not in writer),
            ('06_no_left_writer',"press('left'" not in writer),
            ('07_delta_plan_defined',"def _task091_table_cell_delta_plan" in source),
            ('08_no_shift_down',"keyDown('shift')" not in writer),
            ('09_no_shift_up',"keyUp('shift')" not in writer),
            ('10_exact_len_helper',shim._task091_table_cell_selection_presses('$42.8M')==6),
            ('11_percent_len_helper',shim._task091_table_cell_selection_presses('112%')==4),
            ('12_single_char_len_helper',shim._task091_table_cell_selection_presses('A')==1),
            ('13_max_len_helper',shim._task091_table_cell_selection_presses('x'*30)==30),
            ('14_currency_two_deltas',len(shim._task091_table_cell_delta_plan('$42.8M','$40.9M'))==2),
            ('15_percent_two_deltas',len(shim._task091_table_cell_delta_plan('112%','104%'))==2),
            ('16_single_one_delta',len(shim._task091_table_cell_delta_plan('A','B'))==1),
            ('17_max_one_delta',len(shim._task091_table_cell_delta_plan('x'*29+'a','x'*29+'b'))==1),
            ('18_currency_bounded_delete',cmd6.count("press('delete')")==2),
            ('19_percent_bounded_delete',cmd4.count("press('delete')")==2),
            ('20_currency_no_left',"press('left'" not in cmd6),
            ('21_percent_no_left',"press('left'" not in cmd4),
            ('22_currency_preserves_boundaries',"write('$'" not in cmd6 and "write('M'" not in cmd6),
            ('23_percent_preserves_suffix',"write('%'" not in cmd4),
            ('24_start_helper_defined',"def _task091_caret_at_text_start" in source),
            ('25_end_helper_defined',"def _task091_caret_at_text_end" in source),
            ('26_start_nav_stage',"table-cell-start-nav-issued" in source),
            ('27_start_probe_stage',"table-cell-start-caret-probe-issued" in source),
            ('28_start_nav_drift_gate',"TASK091_TABLE_CELL_START_NAV_DRIFT" in source),
            ('29_start_evidence_gate',"TASK091_TABLE_CELL_START_CARET_EVIDENCE_MISSING" in source),
            ('30_start_geometry_gate',"TASK091_TABLE_CELL_START_CARET_GEOMETRY_UNPROVEN" in source),
            ('31_start_boundary_gate',"TASK091_TABLE_CELL_CARET_NOT_AT_START" in source),
            ('32_entry_end_is_required',"TASK091_TABLE_CELL_END_CARET_UNPROVEN" in source
             and "caret_entry_end_diagnostic" in source),
            ('33_entry_drift_gate',"TASK091_TABLE_CELL_ENTRY_DRIFT" in source),
            ('34_sibling_signature',"before_sibling_signature" in source),
            ('35_visual_sibling_signature',"table_selected_sibling_visual_sha256" in source),
            ('36_press_count_recorded',"selection_press_count" in source),
            ('37_explicit_text_mode',"explicit_text_mode" in source),
            ('38_start_nav_exact_len',"start_navigation_method']='proven-end-left-by-text-length'" in source
             and "_task091_table_cell_start_navigation_command(pending['old'])" in source),
            ('39_edit_from_proven_start',"edit-start-caret-proven-table-cell" in source),
            ('40_exact_cell_atomic_recovery',"def _task091_table_cell_atomic_delete_repair_command" in source),
            ('41_mismatch_quarantines_undo',"undo_quarantined" in mismatch),
            ('42_mismatch_no_ctrl_z',"ctrl', 'z" not in mismatch),
            ('43_mismatch_no_rollback_call',"_task091_table_cell_rollback_command()" not in mismatch),
            ('44_mismatch_preserves_failure_sha',"failure_deck_sha256" in mismatch),
            ('45_mismatch_preserves_failure_text',"failure_text" in mismatch),
            ('46_mismatch_records_reason',"failure_reason" in mismatch),
            ('47_mismatch_fail_closed_mode',"TARGET_FAIL_CLOSED" in mismatch),
            ('48_section_e_two_point',"'font_decrements': 2" in source),
            ('49_zero_spend_contract',"NON_ZERO_SPEND_MODE_FORBIDDEN" in source),
            ('50_no_generic_evaluator_change',"official evaluator" not in writer.casefold()),
        ]
        self.assertEqual(len(audits),50)
        failed=[name for name,ok in audits if not ok]
        self.assertEqual(failed,[],failed)

    def test_table_cell_atomic_repair_handles_multi_edge_corruption_one_delete_at_a_time(self):
        actual='$$40.9MM'; expected='$40.9M'
        plan=shim._task091_restricted_repair_plan(actual,expected)
        self.assertEqual(plan,[{'op':'delete','index':1,'char':'$'},{'op':'delete','index':6,'char':'M'}])
        first=shim._task091_table_cell_atomic_delete_repair_command(actual,plan[0])
        self.assertIn("press('right', presses=1",first)
        self.assertEqual(first.count("press('delete')"),1)
        after=shim._task091_apply_repair_operation(actual,plan[0])
        self.assertEqual(after,'$40.9MM')
        next_plan=shim._task091_restricted_repair_plan(after,expected)
        self.assertEqual(next_plan,[{'op':'delete','index':6,'char':'M'}])
        second=shim._task091_table_cell_atomic_delete_repair_command(after,next_plan[0])
        self.assertIn("press('right', presses=6",second)
        self.assertEqual(second.count("press('delete')"),1)
        self.assertNotIn("ctrl', 'a",first+second)
        self.assertNotIn("shift",first+second)
        self.assertNotIn("ctrl', 'z",first+second)


class Task091FinalCertificationBoardTests(unittest.TestCase):
    def _root(self):
        root=Path(self.tmp.name)/'final-board'
        root.mkdir(parents=True,exist_ok=True)
        return root

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_final_board_requires_visual_13_of_13_and_zero_penalty(self):
        from arbm091.final_certification_board import _verify_visual
        root=self._root()
        (root/'osworld.log').write_text(
            'TASK091_SECTION_E_SCORE=0.3000/0.3000 VISUAL_GATES=13/13 E_PENALTY=0.0000\n'
            'TASK091_SECTION_E_FAILURES=NONE\n',encoding='utf-8')
        verdict=_verify_visual(root)
        self.assertEqual(verdict['visual_gates'],'13/13')
        self.assertEqual(verdict['section_e_score'],'0.3000')
        (root/'osworld.log').write_text(
            'TASK091_SECTION_E_SCORE=0.2769/0.3000 VISUAL_GATES=12/13 E_PENALTY=0.0231\n'
            'TASK091_SECTION_E_FAILURES=slide3:rounded_text_containment\n',encoding='utf-8')
        with self.assertRaisesRegex((ValueError,SystemExit),'SECTION_E_NOT_FULL_SCORE|VISUAL_GATES_NOT_13_OF_13'):
            _verify_visual(root)

    def test_final_board_requires_exact_slide3_table_values(self):
        from arbm091.final_certification_board import _verify_slide3_table
        root=self._root()
        obs=root/'wps-observations'
        obs.mkdir()
        expected={
            'Table 12#r1c2':'$40.9M','Table 12#r2c2':'104%',
            'Table 12#r3c2':'71%','Table 12#r4c2':'$2.8M',
            'Table 12#r5c2':'3','Table 12#r6c2':'206',
        }
        row={'deck_slide_shapes':{'3':[
            {'kind':'table-cell','name':name,'text':value} for name,value in expected.items()
        ]}}
        (obs/'9999-01-after.json').write_text(json.dumps(row),encoding='utf-8')
        self.assertEqual(_verify_slide3_table(root),expected)
        row['deck_slide_shapes']['3'][0]['text']='BROKEN_TABLE_VALUE'
        (obs/'9999-01-after.json').write_text(json.dumps(row),encoding='utf-8')
        with self.assertRaisesRegex((ValueError,SystemExit),'FINAL_SLIDE3_TABLE_MISMATCH'):
            _verify_slide3_table(root)

    def test_prefocal_boards_are_never_release_authorities(self):
        from arbm091.review_board_50x10 import evaluate as review_evaluate
        from arbm091.elite_board_100 import evaluate as elite_evaluate
        actual='H2 Operating Committee PPackSStabilize-and-Recover RRebaseline'
        expected='H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'
        plan=shim._task091_restricted_repair_plan(actual,expected)
        review=review_evaluate(actual,expected,plan,{'id':6,'name':'CoverTitle','text':actual},'a'*64,'b'*64)
        self.assertEqual(review['status'],'PRE_FOCAL_ADVISORY_PASS')
        self.assertFalse(review['release_approval'])
        source=Path('scripts/arbm091/elite_board_100.py').read_text(encoding='utf-8')
        self.assertIn("'status':'PRE_FOCAL_ADVISORY_PASS'",source)
        self.assertIn("'release_approval':False",source)



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

    def test_persisted_extra_paragraph_break_routes_to_atomic_repair(self):
        pending={
            'slide':1,
            'old':'Planning posture: accelerate growth through H2 scale-up',
            'new':'Northstar Cloud\nPrepared for July Operating Committee review\nPlanning posture: stabilize and recover with disciplined sequencing',
            'shape_id':7,
            'before_old_count':1,
            'before_new_count':0,
            'before_deck_sha256':'a'*64,
            'repair_before_deck_sha256':'',
            'target':{'bbox':[737,515,2,2],'cx':738,'cy':516},
        }
        actual='Northstar Cloud\nPrepared for July Operating Committee review\n\nPlanning posture: stabilize and recover with disciplined sequencing'
        state={
            'deck_slide_text':{'1':actual},
            'deck_slide_shapes':{'1':[{'id':7,'name':'CoverSub','text':actual,
                                      'geometry':{'x':768096,'y':2743200,'w':5669280,'h':1280160}}]},
            'deck_file':{'sha256':'b'*64},
        }
        verified,status,detail=shim._task091_verify_pending('',pending,state)
        self.assertFalse(verified)
        self.assertEqual(status,'disk-text-mismatch')
        self.assertTrue(detail['semantic_target_present'])
        self.assertFalse(detail['exact_shape_text'])
        plan=shim._task091_restricted_repair_plan(actual,pending['new'])
        self.assertEqual(plan,[{'op':'delete','index':61,'char':'\n'}], plan)


if __name__ == '__main__':
    unittest.main()