import unittest
from pathlib import Path

class WorkflowWatchdogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = Path('.github/workflows/osworld-v32-official-18.yml').read_text(encoding='utf-8')

    def test_foreground_run_is_hard_bounded(self):
        self.assertIn("ARBM_TASK_SECONDS: '2400'", self.text)
        self.assertIn("ARBM_RUN_MULTIENV_TIMEOUT_SECONDS: '2520'", self.text)
        self.assertIn('timeout --signal=TERM --kill-after=30s "${ARBM_RUN_MULTIENV_TIMEOUT_SECONDS}s" uv run python scripts/python/run_multienv.py', self.text)

    def test_timeout_preserves_forensic_path(self):
        self.assertIn('run-multienv-timeout.txt', self.text)
        upload = self.text.index('- name: Upload shard evidence')
        self.assertIn('if: always()', self.text[upload:upload+180])

if __name__ == '__main__':
    unittest.main()
