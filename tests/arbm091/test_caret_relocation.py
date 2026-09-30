import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from PIL import Image, ImageDraw
from arbm091.semantic_runtime import _fixed_width_caret_delta_geometry


class CaretRelocationTests(unittest.TestCase):
    def _proof(self, prior, new=True, collateral=False):
        with tempfile.TemporaryDirectory() as root:
            obs=Path(root)/'wps-observations'
            obs.mkdir()
            before=Image.new('RGB',(1920,1080),'white')
            after=before.copy()
            ImageDraw.Draw(before).line((680,405,680,443),fill='black')
            if new:
                ImageDraw.Draw(after).line((555,405,555,443),fill='black')
            if collateral:
                ImageDraw.Draw(after).line((600,405,600,443),fill='black')
            before.save(obs/'0011-01-after.png')
            after.save(obs/'0012-02-after.png')
            with mock.patch.dict(os.environ,{'ARBM_WPS_EVIDENCE_DIR':root}):
                return _fixed_width_caret_delta_geometry('0011-01-after','0012-02-after',
                    [545,404,213,40],prior_caret=prior)

    def test_signed_old_caret_removal_does_not_hide_new_start_caret(self):
        self.assertFalse(self._proof(None)['proven'])
        result=self._proof({'proven':True,'bbox':[135,1,1,39]})
        self.assertTrue(result['proven'])
        self.assertEqual(result['bbox'],[10,1,1,39])

    def test_unproven_old_caret_is_not_excluded(self):
        self.assertFalse(self._proof({'proven':False,'bbox':[135,1,1,39]})['proven'])
        self.assertFalse(self._proof({'proven':True,'bbox':[0,0,213,40]})['proven'])

    def test_old_caret_only_or_collateral_change_is_not_new_caret_proof(self):
        old={'proven':True,'bbox':[135,1,1,39]}
        self.assertFalse(self._proof(old,new=False)['proven'])
        self.assertFalse(self._proof(old,collateral=True)['proven'])
