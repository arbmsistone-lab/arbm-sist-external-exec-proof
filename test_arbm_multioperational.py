import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class MultiOperationalPolicyTests(unittest.TestCase):
    def read(self, relative):
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_exactly_three_critical_executor_routes(self):
        from arbm_executor_contract import PROVIDERS
        self.assertEqual(PROVIDERS, ("github", "gitlab", "arbm-external"))

    def test_github_adapter_uses_common_contract(self):
        text = self.read(".github/workflows/p9-dubbo-m0031-eval.yml")
        self.assertIn("python arbm_executor_contract.py", text)
        self.assertIn("executor-context.json", text)

    def test_gitlab_adapter_uses_common_contract(self):
        text = self.read(".gitlab-ci.yml")
        self.assertIn('GITLAB_CI: "true"', text)
        self.assertIn("python arbm_executor_contract.py", text)

    def test_external_adapter_uses_common_contract(self):
        text = self.read("arbm-external-p9.sh")
        self.assertIn("ARBM_EXTERNAL_EXEC", text)
        self.assertIn("ARBM_FREE_CAPACITY_PROVEN", text)
        self.assertIn("python arbm_executor_contract.py", text)

    def test_all_routes_are_fail_closed_on_zero_spend(self):
        contract = self.read("arbm_executor_contract.py")
        observer = self.read("p9-evaluator-observe.py")
        self.assertIn('ZERO_SPEND_MODE") != "HARD"', contract)
        self.assertIn("build_context()", observer)


if __name__ == "__main__":
    unittest.main()
