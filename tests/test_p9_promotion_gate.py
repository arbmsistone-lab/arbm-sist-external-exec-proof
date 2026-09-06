"""Synthetic unit cases only: these are not benchmark evidence."""
import copy
from pathlib import Path
import runpy
import unittest

verify = runpy.run_path(str(Path(__file__).resolve().parents[1]/'p9-promotion-result-gate.py'))['failures']

class GateTests(unittest.TestCase):
    def setUp(self):
        self.d = dict(milestone_id='M003.1', patch_exists=True, patch_successfully_applied=True, resolved=True,
            build_failure_policy=dict(fail_closed=True, partial_test_universe=False), infrastructure_failure='', infra_invalid=False, infra_invalid_reason='',
            snapshot_integrity=dict(ok=True, legacy_unverified=False),
            evaluation_environment=dict(repo_config_binding_mode='trial-pinned', repo_config_sha256='ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356', runtime_policy_binding_mode='trial-pinned', runtime_policy_mode='protected', runtime_policy_sha256='aa7ec051587f229ac4ac9d3822f2b90790cac551f61a1c284d5664ad45728f1f'),
            test_summary=dict(pass_to_pass_required=6954, pass_to_pass_achieved=6954, none_to_pass_required=1, none_to_pass_achieved=1, fail_to_pass_required=0, fail_to_pass_achieved=0, pass_to_pass_failed=0, pass_to_pass_missing=0, none_to_pass_missing=0))

    def test_complete_contract(self):
        self.assertEqual(verify(self.d), [])

    def test_missing_fields_rejected(self):
        for key in self.d:
            d = copy.deepcopy(self.d)
            del d[key]
            with self.subTest(key=key):
                self.assertTrue(verify(d))

    def test_partial_tests_rejected(self):
        for field in ['pass_to_pass_achieved', 'none_to_pass_achieved']:
            d = copy.deepcopy(self.d)
            d['test_summary'][field] -= 1
            self.assertTrue(verify(d))

    def test_false_green_rejected(self):
        for path, value in [(('build_failure_policy','fail_closed'), False), (('build_failure_policy','partial_test_universe'), True), (('snapshot_integrity','legacy_unverified'), True), (('snapshot_integrity','ok'), None), (('evaluation_environment','runtime_policy_binding_mode'), 'legacy-live'), (('test_summary','pass_to_pass_required'), 1), (('test_summary','none_to_pass_missing'), 1)]:
            d = copy.deepcopy(self.d)
            d[path[0]][path[1]] = value
            self.assertTrue(verify(d), path)

if __name__ == '__main__':
    unittest.main()
