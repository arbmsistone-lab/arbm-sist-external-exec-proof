import os
import pathlib
import sys
import tempfile
import unittest
import unittest.mock as mock

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import osworld_061_lane_receipt as receipt


class LaneReceiptTests(unittest.TestCase):
    def test_timeout_124_is_explicit(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {
            'GITHUB_SHA': 'a' * 40, 'ZERO_SPEND_MODE': 'HARD'}):
            old = os.getcwd(); os.chdir(d)
            try: out = receipt.build('fast', 124, 100, 145)
            finally: os.chdir(old)
        self.assertTrue(out['timed_out'])
        self.assertFalse(out['success'])
        self.assertEqual(out['elapsed_seconds'], 45)

    def test_success_receipt_preserves_zero_spend(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {
            'GITHUB_SHA': 'b' * 40, 'ZERO_SPEND_MODE': 'HARD'}):
            old = os.getcwd(); os.chdir(d)
            try: out = receipt.build('full', 0, 100, 101)
            finally: os.chdir(old)
        self.assertTrue(out['success'])
        self.assertFalse(out['paid_fallback_used'])
        self.assertEqual(out['heavy_local'], 0)
        self.assertEqual(out['zero_spend_mode'], 'HARD')

    def test_invalid_lane_and_time_are_rejected(self):
        with self.assertRaises(ValueError): receipt.build('other', 0, 1, 2)
        with self.assertRaises(ValueError): receipt.build('fast', 0, 2, 1)


if __name__ == '__main__':
    unittest.main()
