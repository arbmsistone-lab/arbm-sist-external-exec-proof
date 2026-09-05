import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('constitution', Path(__file__).with_name('arbm-constitution.py'))
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class TechnicalConstitutionTests(unittest.TestCase):
    def test_frozen_policy(self):
        self.assertEqual(policy.validate(dict(policy.REQUIRED)), [])

    def test_every_missing_or_changed_invariant_fails_closed(self):
        for key, value in policy.REQUIRED.items():
            with self.subTest(key=key):
                sample = dict(policy.REQUIRED)
                del sample[key]
                self.assertIn('CONSTITUTION_VIOLATION:'+key, policy.validate(sample))
                sample[key] = not value if isinstance(value, bool) else 'UNAPPROVED'
                self.assertIn('CONSTITUTION_VIOLATION:'+key, policy.validate(sample))

    def test_integer_cannot_impersonate_boolean(self):
        sample = dict(policy.REQUIRED, paidInferenceAllowed=0)
        self.assertIn('CONSTITUTION_VIOLATION:paidInferenceAllowed', policy.validate(sample))

    def test_soft_mode_is_rejected(self):
        for mode in ('SOFT', '', None, '0'):
            self.assertIn('CONSTITUTION_VIOLATION:ZERO_SPEND_MODE', policy.validate(dict(policy.REQUIRED), mode))

    def test_non_object_policy_is_rejected(self):
        for value in (None, [], False):
            self.assertTrue(policy.validate(value))


if __name__ == '__main__':
    unittest.main(verbosity=2)
