import unittest
from pathlib import Path

import arbm_executor_contract as contract


class ExecutorContractTests(unittest.TestCase):
    def base(self):
        return {"ZERO_SPEND_MODE": "HARD", "ARBM_WORKSPACE": str(Path.cwd())}

    def test_github_route(self):
        env = self.base() | {
            "GITHUB_ACTIONS": "true", "RUNNER_ENVIRONMENT": "github-hosted",
            "ARBM_REPO_VISIBILITY": "public", "RUNNER_NAME": "gh-free"}
        self.assertEqual(contract.build_context(env).provider, "github")

    def test_gitlab_route(self):
        env = self.base() | {
            "GITLAB_CI": "true", "ARBM_GITLAB_FREE_RUNNER": "true",
            "CI_RUNNER_DESCRIPTION": "gl-free"}
        self.assertEqual(contract.build_context(env).provider, "gitlab")

    def test_external_route(self):
        env = self.base() | {
            "ARBM_EXTERNAL_EXEC": "true", "ARBM_FREE_CAPACITY_PROVEN": "true",
            "ARBM_RUNNER_NAME": "external-free"}
        self.assertEqual(contract.build_context(env).provider, "arbm-external")

    def test_rejects_ambiguous_provider(self):
        env = self.base() | {
            "GITHUB_ACTIONS": "true", "GITLAB_CI": "true",
            "RUNNER_ENVIRONMENT": "github-hosted", "ARBM_REPO_VISIBILITY": "public",
            "ARBM_GITLAB_FREE_RUNNER": "true"}
        with self.assertRaisesRegex(RuntimeError, "EXECUTOR_PROVIDER_INVALID"):
            contract.build_context(env)

    def test_rejects_unproven_free_capacity(self):
        env = self.base() | {"ARBM_EXTERNAL_EXEC": "true"}
        with self.assertRaisesRegex(RuntimeError, "FREE_CAPACITY_NOT_PROVEN"):
            contract.build_context(env)

    def test_rejects_non_hard_zero_spend(self):
        env = {"ARBM_EXTERNAL_EXEC": "true", "ARBM_FREE_CAPACITY_PROVEN": "true"}
        with self.assertRaisesRegex(RuntimeError, "ZERO_SPEND_MODE_REQUIRED"):
            contract.build_context(env)


if __name__ == "__main__":
    unittest.main()
