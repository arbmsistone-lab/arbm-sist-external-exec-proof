import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import osworld_061_heavy_runtime_preflight as preflight


class HeavyRuntimePreflightTests(unittest.TestCase):
    def test_capacity_thresholds_are_conservative(self):
        self.assertGreaterEqual(preflight.MIN_AVAILABLE_MEMORY_BYTES, 4 * 1024**3)
        self.assertGreaterEqual(preflight.MIN_FREE_DISK_BYTES, 8 * 1024**3)

    def test_exact_runtime_skips_install(self):
        versions = dict(preflight.REQUIRED)
        with mock.patch.object(preflight, '_memory_available_bytes', return_value=8 * 1024**3), \
             mock.patch.object(preflight.shutil, 'disk_usage') as usage, \
             mock.patch.object(preflight, '_installed_versions', return_value=versions), \
             mock.patch.dict(os.environ, {'ZERO_SPEND_MODE': 'HARD', 'RUNNER_ENVIRONMENT': 'github-hosted'}):
            usage.return_value.free = 20 * 1024**3
            report = preflight.evaluate('.')
        self.assertTrue(report['capacity_ok'])
        self.assertTrue(report['exact_runtime_present'])
        self.assertFalse(report['install_required'])
        self.assertEqual(report['status'], 'HEAVY_RUNTIME_PREFLIGHT_PASS')

    def test_version_mismatch_requires_install(self):
        versions = dict(preflight.REQUIRED)
        versions['torch'] = '0.0.0'
        with mock.patch.object(preflight, '_memory_available_bytes', return_value=8 * 1024**3), \
             mock.patch.object(preflight.shutil, 'disk_usage') as usage, \
             mock.patch.object(preflight, '_installed_versions', return_value=versions), \
             mock.patch.dict(os.environ, {'ZERO_SPEND_MODE': 'HARD', 'RUNNER_ENVIRONMENT': 'github-hosted'}):
            usage.return_value.free = 20 * 1024**3
            report = preflight.evaluate('.')
        self.assertTrue(report['install_required'])
        self.assertEqual(report['status'], 'HEAVY_RUNTIME_PREFLIGHT_PASS')

    def test_insufficient_memory_blocks_even_if_versions_match(self):
        with mock.patch.object(preflight, '_memory_available_bytes', return_value=1024**3), \
             mock.patch.object(preflight.shutil, 'disk_usage') as usage, \
             mock.patch.object(preflight, '_installed_versions', return_value=dict(preflight.REQUIRED)), \
             mock.patch.dict(os.environ, {'ZERO_SPEND_MODE': 'HARD', 'RUNNER_ENVIRONMENT': 'github-hosted'}):
            usage.return_value.free = 20 * 1024**3
            report = preflight.evaluate('.')
        self.assertFalse(report['capacity_ok'])
        self.assertEqual(report['status'], 'HEAVY_RUNTIME_PREFLIGHT_BLOCKED')

    def test_non_hard_or_non_github_hosted_blocks(self):
        with mock.patch.object(preflight, '_memory_available_bytes', return_value=8 * 1024**3), \
             mock.patch.object(preflight.shutil, 'disk_usage') as usage, \
             mock.patch.object(preflight, '_installed_versions', return_value=dict(preflight.REQUIRED)), \
             mock.patch.dict(os.environ, {'ZERO_SPEND_MODE': 'SOFT', 'RUNNER_ENVIRONMENT': 'self-hosted'}):
            usage.return_value.free = 20 * 1024**3
            report = preflight.evaluate('.')
        self.assertFalse(report['zero_spend_hard'])
        self.assertFalse(report['github_hosted'])
        self.assertEqual(report['status'], 'HEAVY_RUNTIME_PREFLIGHT_BLOCKED')


if __name__ == '__main__':
    unittest.main()
