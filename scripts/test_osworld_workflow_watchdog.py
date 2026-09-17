import unittest
from pathlib import Path


class WorkflowWatchdogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = Path('.github/workflows/osworld-v32-official-18.yml').read_text(encoding='utf-8')
        cls.audit = Path('.github/workflows/osworld-061-world-audit.yml').read_text(encoding='utf-8')

    def test_foreground_run_is_hard_bounded(self):
        self.assertIn("ARBM_TASK_SECONDS: '2400'", self.text)
        self.assertIn("ARBM_RUN_MULTIENV_TIMEOUT_SECONDS: '2520'", self.text)
        self.assertIn('timeout --signal=TERM --kill-after=30s "${ARBM_RUN_MULTIENV_TIMEOUT_SECONDS}s" uv run python scripts/python/run_multienv.py', self.text)

    def test_timeout_preserves_forensic_path(self):
        self.assertIn('run-multienv-timeout.txt', self.text)
        upload = self.text.index('- name: Upload shard evidence')
        self.assertIn('if: always()', self.text[upload:upload+180])

    def test_world_audit_fast_path_is_bounded_and_zero_spend(self):
        self.assertIn("ZERO_SPEND_MODE: HARD", self.audit)
        self.assertIn("ARBM_SWARM_REMOTE_WORKERS: '3'", self.audit)
        self.assertIn('Run 10-robot specialist remote fast path', self.audit)
        self.assertIn('python scripts/osworld_061_performance_swarm.py incident-evidence', self.audit)

    def test_heavy_runtime_is_fallback_only(self):
        marker = '- name: Install heavyweight local audit fallback'
        start = self.audit.index(marker)
        block = self.audit[start:start+700]
        self.assertIn("if: steps.swarm_fast.outcome != 'success'", block)
        self.assertIn("'torch==2.7.1'", block)
        self.assertIn("'transformers==4.52.4'", block)
        self.assertIn("'safetensors==0.8.0'", block)

    def test_full_swarm_remains_fail_closed_fallback(self):
        marker = '- name: Run full specialist failover'
        start = self.audit.index(marker)
        block = self.audit[start:start+500]
        self.assertIn("if: steps.swarm_fast.outcome != 'success'", block)
        self.assertIn('python scripts/osworld_061_evidence_aware_swarm.py incident-evidence', block)

    def test_supreme_verdict_requires_a_swarm_and_3d_success(self):
        marker = '- name: Enforce supreme audit verdict'
        start = self.audit.index(marker)
        block = self.audit[start:start+700]
        self.assertIn('steps.swarm_fast.outcome', block)
        self.assertIn('steps.swarm_full.outcome', block)
        self.assertIn('SPECIALIST_SWARM_NOT_ACCEPTED', block)
        self.assertIn('steps.audit3d.outcome', block)

    def test_push_scope_remains_official_branch_only(self):
        self.assertIn('branches: [chatgpt/arbm-agent-elite-v2-20260914]', self.audit)
        self.assertNotIn('chatgpt/arbm-sist-performance-hardening-20260917', self.audit)


if __name__ == '__main__':
    unittest.main()
