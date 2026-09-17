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

    def test_world_audit_permissions_are_read_only(self):
        permissions = self.audit[self.audit.index('permissions:'):self.audit.index('concurrency:')]
        self.assertIn('actions: read', permissions)
        self.assertIn('contents: read', permissions)
        for forbidden in ('write', 'id-token:', 'packages:', 'pull-requests:', 'issues:'):
            self.assertNotIn(forbidden, permissions)

    def test_world_audit_serializes_same_ref_without_killing_valid_run(self):
        block = self.audit[self.audit.index('concurrency:'):self.audit.index('jobs:')]
        self.assertIn('group: osworld-061-world-audit-${{ github.ref }}', block)
        self.assertIn('cancel-in-progress: false', block)

    def test_checkout_does_not_persist_credentials(self):
        self.assertIn('actions/checkout@11d5960a326750d5838078e36cf38b85af677262', self.audit)
        checkout = self.audit[self.audit.index('actions/checkout@'):self.audit.index('- name: Purge stale')]
        self.assertIn('persist-credentials: false', checkout)

    def test_world_audit_fast_path_is_bounded_and_zero_spend(self):
        self.assertIn('ZERO_SPEND_MODE: HARD', self.audit)
        self.assertIn("ARBM_LOCAL_TEXT_CACHE_MODELS: '1'", self.audit)
        self.assertIn("ARBM_SWARM_REMOTE_WORKERS: '3'", self.audit)
        self.assertIn("ARBM_SWARM_OPENROUTER_BUDGET_S: '45'", self.audit)
        self.assertIn("ARBM_SWARM_GROQ_BUDGET_S: '30'", self.audit)
        self.assertIn("ARBM_SWARM_REPAIR_BUDGET_S: '20'", self.audit)
        self.assertIn('timeout --signal=TERM --kill-after=10s 360s python scripts/osworld_061_performance_swarm.py incident-evidence', self.audit)

    def test_installations_refuse_source_builds(self):
        self.assertGreaterEqual(self.audit.count('--only-binary=:all:'), 2)

    def test_deterministic_audits_have_process_deadlines(self):
        self.assertIn('timeout --signal=TERM --kill-after=10s 60s python scripts/osworld_061_champion_audit.py', self.audit)
        self.assertIn('timeout --signal=TERM --kill-after=10s 60s python scripts/osworld_061_3d_audit.py incident-evidence', self.audit)

    def test_heavy_runtime_preflight_is_fail_closed(self):
        marker = '- name: Preflight heavyweight local audit fallback'
        start = self.audit.index(marker)
        block = self.audit[start:start+650]
        self.assertIn('id: heavy_preflight', block)
        self.assertIn("steps.swarm_fast.outputs.fallback_eligible == '1'", block)
        self.assertIn('python scripts/osworld_061_heavy_runtime_preflight.py', block)
        install = self.audit[self.audit.index('- name: Install heavyweight local audit fallback'):]
        self.assertIn("steps.heavy_preflight.outputs.capacity_ok == '1'", install)
        self.assertIn("steps.heavy_preflight.outputs.install_required == '1'", install)

    def test_heavy_runtime_is_pinned_verified_and_bounded(self):
        marker = '- name: Install heavyweight local audit fallback'
        start = self.audit.index(marker)
        block = self.audit[start:start+1500]
        self.assertIn("'torch==2.7.1'", block)
        self.assertIn("'transformers==4.52.4'", block)
        self.assertIn("'safetensors==0.8.0'", block)
        self.assertIn('timeout --signal=TERM --kill-after=20s 240s', block)
        self.assertIn('- name: Verify heavyweight local audit runtime', block)
        self.assertIn("required={'torch':'2.7.1','transformers':'4.52.4','safetensors':'0.8.0'}", block)
        self.assertIn('assert actual==required', block)

    def test_full_swarm_remains_bounded_fail_closed_fallback(self):
        marker = '- name: Run full specialist failover'
        start = self.audit.index(marker)
        block = self.audit[start:start+700]
        self.assertIn("steps.swarm_fast.outputs.fallback_eligible == '1'", block)
        self.assertIn('timeout --signal=TERM --kill-after=20s 900s python scripts/osworld_061_evidence_aware_swarm.py incident-evidence', block)

    def test_substantive_blocker_cannot_be_erased_by_fallback(self):
        marker = '- name: Enforce supreme audit verdict'
        start = self.audit.index(marker)
        block = self.audit[start:start+900]
        self.assertIn('steps.swarm_fast.outputs.substantive_blocked', block)
        self.assertIn('SUBSTANTIVE_SPECIALIST_BLOCKER', block)
        self.assertIn('SPECIALIST_SWARM_NOT_ACCEPTED', block)
        self.assertIn('steps.audit3d.outcome', block)

    def test_fast_path_and_heavy_preflight_forensics_are_preserved(self):
        marker = '- name: Preserve world-audit evidence'
        block = self.audit[self.audit.index(marker):]
        self.assertIn('osworld-061-specialist-fast-path.json', block)
        self.assertIn('osworld-061-heavy-runtime-preflight.json', block)
        self.assertIn('osworld-061-specialist-swarm.json', block)
        self.assertIn('if: always()', block[:220])

    def test_push_scope_remains_official_branch_only(self):
        self.assertIn('branches: [chatgpt/arbm-agent-elite-v2-20260914]', self.audit)
        self.assertNotIn('chatgpt/arbm-sist-performance-hardening-20260917', self.audit)


if __name__ == '__main__':
    unittest.main()
