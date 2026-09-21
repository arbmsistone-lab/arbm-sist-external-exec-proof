import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, ImageDraw

from arbm_senior_elite_board import review_action, require_unanimous
import osworld_free_mesh_shim as shim


class SeniorEliteBoardTests(unittest.TestCase):
    def _valid(self):
        return {
            'action':'exec',
            'command':"pyautogui.click(100, 100)",
            'target':{'source':'accessibility','role':'button','label':'OK'},
        }

    def test_valid_action_requires_unanimous_10_of_10(self):
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','GITHUB_SHA':'a'*40},clear=False):
            result=review_action(self._valid(),task_id='001',source='generic-mesh',
                                 state={},verifier={'progress':True,'no_progress':0},
                                 recent_commands=[])
        self.assertTrue(result['allow'])
        self.assertEqual(result['pass'],10)
        self.assertEqual(result['total'],10)
        self.assertTrue(result['unanimous'])

    def test_task091_specialist_cannot_be_bypassed(self):
        state={'task091_specialist':{'owned':True,'handoff':False}}
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','GITHUB_SHA':'b'*40},clear=False):
            result=review_action(self._valid(),task_id='091',source='generic-mesh',
                                 state=state,verifier={'progress':True,'no_progress':0},
                                 recent_commands=[])
        self.assertFalse(result['allow'])
        self.assertIn('specialist_ownership',result['failed'])

    def test_security_vetoes_shell_capability(self):
        action={'action':'exec',"command":"pyautogui.hotkey('ctrl','alt','t')"}
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','GITHUB_SHA':'c'*40},clear=False):
            result=review_action(action,task_id='001',source='generic-mesh',
                                 state={},verifier={'progress':True,'no_progress':0})
        self.assertFalse(result['allow'])
        self.assertIn('security',result['failed'])

    def test_zero_spend_is_hard_gate(self):
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'OFF','GITHUB_SHA':'d'*40},clear=False):
            with self.assertRaisesRegex(ValueError,'SENIOR_ELITE_VETO:.*zero_spend'):
                require_unanimous(self._valid(),task_id='001',source='generic-mesh',
                                  state={},verifier={'progress':True,'no_progress':0})

    def test_repeat_after_no_progress_is_vetoed(self):
        action=self._valid()
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','GITHUB_SHA':'e'*40},clear=False):
            result=review_action(action,task_id='001',source='generic-mesh',
                                 state={},verifier={'progress':False,'no_progress':1},
                                 recent_commands=[action['command']])
        self.assertFalse(result['allow'])
        self.assertIn('anti_repetition',result['failed'])

    def test_task091_table_text_mode_path_is_separate_single_click(self):
        command="pyautogui.click(843, 452)"
        self.assertEqual(command,"pyautogui.click(843, 452)")
        self.assertNotIn("doubleClick", command)

    def test_task091_second_table_click_uses_issued_command_hash_not_shape_center(self):
        command="pyautogui.click(843, 404)"
        state={'task091_specialist':{
            'owned':True,'handoff':False,
            'pending_edit':{
                'stage':'table-cell-enter-issued','shape_kind':'table-cell','slide':3,
                'target':{'cx':811,'cy':391},
                'cell_enter_command_hash':hashlib.sha256(command.encode()).hexdigest(),
                'table_selected_screenshot_sha256':'1'*64,
                'table_selected_target_visual_sha256':'2'*64,
                'table_selected_sibling_visual_sha256':'3'*64,
            },
        }}
        action={'action':'exec','command':command,'specialist_phase':'enter-table-cell-caret-candidate',
                'target':{'source':'task091-pptx-canonical','slide':3,'role':'task091-canonical-point','label':'$42.8M'}}
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','GITHUB_SHA':'f'*40},clear=False):
            result=review_action(action,task_id='091',source='task091-specialist',
                                 state=state,verifier={'progress':False,'no_progress':1},
                                 recent_commands=[command])
        self.assertTrue(result['allow'],result)
        self.assertEqual(result['pass'],10)

    def test_task091_second_table_click_hash_mismatch_is_vetoed(self):
        command="pyautogui.click(843, 404)"
        state={'task091_specialist':{
            'owned':True,'handoff':False,
            'pending_edit':{
                'stage':'table-cell-enter-issued','shape_kind':'table-cell','slide':3,
                'cell_enter_command_hash':'0'*64,
                'table_selected_screenshot_sha256':'1'*64,
                'table_selected_target_visual_sha256':'2'*64,
                'table_selected_sibling_visual_sha256':'3'*64,
            },
        }}
        action={'action':'exec','command':command,'specialist_phase':'enter-table-cell-caret-candidate',
                'target':{'source':'task091-pptx-canonical','slide':3,'role':'task091-canonical-point','label':'$42.8M'}}
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','GITHUB_SHA':'f'*40},clear=False):
            result=review_action(action,task_id='091',source='task091-specialist',
                                 state=state,verifier={'progress':False,'no_progress':1},
                                 recent_commands=[command])
        self.assertFalse(result['allow'])
        self.assertIn('anti_repetition',result['failed'])


class TableTextInkTests(unittest.TestCase):
    def _state(self, source):
        return {'source':source,'screenshot_sha256':'a'*64}

    def test_table_text_ink_point_tracks_visible_glyph_band_not_cell_center(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            obs=root/'wps-observations'
            obs.mkdir()
            image=Image.new('RGB',(240,140),'white')
            draw=ImageDraw.Draw(image)
            # Synthetic glyph-like strokes in the upper text band of the cell.
            draw.rectangle((96,49,101,63),fill='black')
            draw.rectangle((104,49,109,63),fill='black')
            draw.rectangle((112,49,117,63),fill='black')
            image.save(obs/'0001-01-after.png')
            with patch.dict(os.environ,{'ARBM_WPS_EVIDENCE_DIR':str(root)},clear=False):
                point=shim._task091_table_cell_text_ink_point(
                    self._state('0001-01-after'),[60,35,140,80])
            self.assertIsNotNone(point)
            self.assertEqual(len(point['proof_sha256']),64)
            self.assertGreaterEqual(point['cx'],96)
            self.assertLessEqual(point['cx'],117)
            self.assertGreaterEqual(point['cy'],49)
            self.assertLessEqual(point['cy'],63)
            self.assertLess(point['cy'],35+80//2)

    def test_table_text_ink_point_rejects_blank_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            obs=root/'wps-observations'
            obs.mkdir()
            Image.new('RGB',(240,140),'white').save(obs/'0001-01-after.png')
            with patch.dict(os.environ,{'ARBM_WPS_EVIDENCE_DIR':str(root)},clear=False):
                point=shim._task091_table_cell_text_ink_point(
                    self._state('0001-01-after'),[60,35,140,80])
            self.assertIsNone(point)


class CaretEvidenceSourceContractTests(unittest.TestCase):
    def test_runtime_source_regex_accepts_canonical_observation_ids(self):
        source = '0042-01-after'
        self.assertRegex(source, r'\d{4}-\d{2}-(?:before|after)')

    def test_runtime_source_regex_rejects_untrusted_paths(self):
        self.assertNotRegex('/tmp/0042-01-after.png', r'^\d{4}-\d{2}-(?:before|after)$')


class CaretGeometryTests(unittest.TestCase):
    def test_one_pixel_vertical_delta_is_proven_caret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            obs=root/'wps-observations'
            obs.mkdir()
            a=Image.new('RGB',(220,120),'white')
            b=a.copy()
            draw=ImageDraw.Draw(b)
            draw.line((111,43,111,64),fill='black',width=1)
            a.save(obs/'0001-01-after.png')
            b.save(obs/'0002-01-after.png')
            with patch.dict(os.environ,{'ARBM_WPS_EVIDENCE_DIR':str(root)},clear=False):
                result=shim._task091_caret_delta_geometry(
                    '0001-01-after','0002-01-after',[20,20,180,80])
            self.assertTrue(result['proven'],result)
            self.assertLessEqual(result['width'],4)
            self.assertGreaterEqual(result['height'],8)

    def test_identical_frames_are_not_caret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); obs=root/'wps-observations'; obs.mkdir()
            a=Image.new('RGB',(220,120),'white')
            a.save(obs/'0001-01-after.png'); a.save(obs/'0002-01-after.png')
            with patch.dict(os.environ,{'ARBM_WPS_EVIDENCE_DIR':str(root)},clear=False):
                result=shim._task091_caret_delta_geometry(
                    '0001-01-after','0002-01-after',[20,20,180,80])
            self.assertFalse(result['proven'],result)
            self.assertEqual(result['reason'],'no-local-delta')

    def test_delta_outside_cell_is_not_caret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); obs=root/'wps-observations'; obs.mkdir()
            a=Image.new('RGB',(220,120),'white'); b=a.copy()
            ImageDraw.Draw(b).line((210,43,210,64),fill='black',width=1)
            a.save(obs/'0001-01-after.png'); b.save(obs/'0002-01-after.png')
            with patch.dict(os.environ,{'ARBM_WPS_EVIDENCE_DIR':str(root)},clear=False):
                result=shim._task091_caret_delta_geometry(
                    '0001-01-after','0002-01-after',[20,20,180,80])
            self.assertFalse(result['proven'],result)
            self.assertEqual(result['reason'],'no-local-delta')

    def test_broad_rectangle_is_not_caret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            obs=root/'wps-observations'
            obs.mkdir()
            a=Image.new('RGB',(220,120),'white')
            b=a.copy()
            draw=ImageDraw.Draw(b)
            draw.rectangle((90,40,130,75),fill='black')
            a.save(obs/'0001-01-after.png')
            b.save(obs/'0002-01-after.png')
            with patch.dict(os.environ,{'ARBM_WPS_EVIDENCE_DIR':str(root)},clear=False):
                result=shim._task091_caret_delta_geometry(
                    '0001-01-after','0002-01-after',[20,20,180,80])
            self.assertFalse(result['proven'],result)


if __name__ == '__main__':
    unittest.main()
