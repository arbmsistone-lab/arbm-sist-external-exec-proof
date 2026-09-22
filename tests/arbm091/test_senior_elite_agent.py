import os
import hashlib
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


    def test_task091_end_caret_bounded_replace_passes_all_ten_lanes(self):
        command=shim._task091_table_cell_bounded_write_command('$42.8M','$40.9M')
        action={'action':'exec','command':command,'specialist_phase':'edit-end-caret-proven-table-cell'}
        state={'task091_specialist':{'owned':True,'handoff':False}}
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','GITHUB_SHA':'1'*40},clear=False):
            result=review_action(action,task_id='091',source='task091-specialist',
                                 state=state,verifier={'progress':True,'no_progress':0},
                                 recent_commands=[])
        self.assertTrue(result['allow'],result)
        self.assertEqual(result['pass'],10)


    def test_task091_second_table_click_allows_only_evidence_bound_second_attempt(self):
        command="pyautogui.click(843, 404)"
        digest=hashlib.sha256(command.encode()).hexdigest()
        state={'task091_specialist':{'owned':True,'handoff':False,'pending_edit':{
            'stage':'table-cell-enter-issued','shape_kind':'table-cell','slide':3,
            'cell_enter_command_hash':digest,'cell_text_hit_command_hash':digest,
            'textmode_baseline_source':'0041-01-after','textmode_first_hit_source':'0042-01-after',
            'table_selected_screenshot_sha256':'1'*64,
            'table_selected_target_visual_sha256':'2'*64,
            'table_selected_sibling_visual_sha256':'3'*64}}}
        action={'action':'exec','command':command,'specialist_phase':'enter-table-cell-caret-candidate',
                'target':{'source':'task091-pptx-canonical','slide':3}}
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','GITHUB_SHA':'f'*40},clear=False):
            result=review_action(action,task_id='091',source='task091-specialist',state=state,
                                 verifier={'progress':False,'no_progress':9},recent_commands=[command])
        self.assertTrue(result['allow'],result)
        self.assertEqual(result['pass'],10)

    def test_task091_third_identical_table_click_remains_vetoed(self):
        command="pyautogui.click(843, 404)"
        digest=hashlib.sha256(command.encode()).hexdigest()
        state={'task091_specialist':{'owned':True,'handoff':False,'pending_edit':{
            'stage':'table-cell-enter-issued','shape_kind':'table-cell','slide':3,
            'cell_enter_command_hash':digest,'cell_text_hit_command_hash':digest,
            'textmode_baseline_source':'0041-01-after','textmode_first_hit_source':'0042-01-after',
            'table_selected_screenshot_sha256':'1'*64,
            'table_selected_target_visual_sha256':'2'*64,
            'table_selected_sibling_visual_sha256':'3'*64}}}
        action={'action':'exec','command':command,'specialist_phase':'enter-table-cell-caret-candidate',
                'target':{'source':'task091-pptx-canonical','slide':3}}
        with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','GITHUB_SHA':'f'*40},clear=False):
            result=review_action(action,task_id='091',source='task091-specialist',state=state,
                                 verifier={'progress':False,'no_progress':10},recent_commands=[command,command])
        self.assertFalse(result['allow'])
        self.assertIn('anti_repetition',result['failed'])


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
