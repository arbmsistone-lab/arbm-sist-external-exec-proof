from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PROMO = (ROOT/'.github/workflows/p9-dubbo-m0031-promote.yml').read_text(encoding='utf-8')
CLOUD = (ROOT/'.github/workflows/p9-dubbo-m0031-cloud-plan.yml').read_text(encoding='utf-8')

class P9WorkflowContractTests(unittest.TestCase):
    def test_runtime_policy_binding_is_fail_closed_and_preflighted(self):
        self.assertIn("'runtime_policy_binding':RuntimePolicyIdentity", PROMO)
        self.assertIn('--runtime-policy p9-bindings/runtime_policy.yaml', PROMO)
        self.assertIn('--runtime-policy-sha256 "$RUNTIME_POLICY_SHA256"', PROMO)
        self.assertIn('--runtime-policy-mode protected', PROMO)
        self.assertIn('Preflight trial-pinned runtime policy contract', PROMO)
        self.assertLess(PROMO.index('Preflight trial-pinned runtime policy contract'), PROMO.index('Pull pinned official image'))

    def test_cloud_plan_uses_verified_srs_and_valid_python_split(self):
        self.assertIn('aac87b7e8a66001512c9c54649b3e1571d252777177d52cbed197fc541dd164f', CLOUD)
        self.assertNotIn('5cbb7e308d284ea177e3c4c5c258fd2b17ada41943e012569cebbbb7c7b45b2d', CLOUD)
        self.assertNotIn("indent=2))          evidence={", CLOUD)
        self.assertIn("indent=2))\n          evidence={", CLOUD)

if __name__ == '__main__':
    unittest.main()
