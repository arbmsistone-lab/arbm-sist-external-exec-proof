from pathlib import Path
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'f26ba87020ceaefc01d22e0a592fbc864d0d9291'


class WorkflowTests(unittest.TestCase):
    def workflow(self, suffix):
        return yaml.safe_load((ROOT / '.github/workflows' / ('osworld-g3-paid-' + suffix + '.yml')).read_text())

    def test_paid_lanes_share_budget_lock_and_gate_before_work(self):
        for suffix, job_name in [('smoke-v2', 'smoke'), ('model-probe', 'probe')]:
            flow = self.workflow(suffix)
            self.assertEqual(flow['concurrency'], {'group': 'arbm-g3-paid-total-budget', 'cancel-in-progress': False})
            job = flow['jobs'][job_name]
            self.assertIn("refs/heads/g3/paid-cert-lane-20260910", job['if'])
            self.assertIn('arbmsistone-lab/arbm-sist-external-exec-proof', job['if'])
            self.assertIn('g3_paid_control.py', job['steps'][1]['run'])
            self.assertEqual(flow[True]['push']['paths'],
                             ['.g3-paid-smoke-trigger' if job_name == 'smoke' else '.g3-paid-probe-trigger'])

    def test_smoke_pins_and_harness_contract_preserved(self):
        flow = self.workflow('smoke-v2')
        body = '\n'.join(step.get('run', '') for step in flow['jobs']['smoke']['steps'])
        for required in ['v2026.08.08', 'd578d2d4e0dc82b43e270fdaa7fa89d9708cd154',
                         'sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9',
                         '8213366932c553e5fe758d0f2c8c8b81ffc3be8c',
                         'eb737ae70b49849e24af407de6a518439a23de05a8497096a948334ce0a909aa',
                         '--max_steps 100', '--num_envs 1', '--eval_version v2', '--model gemini-3.5-flash']:
            self.assertIn(required, body)
        # Agent integration patches may change the harness, never task/evaluator.
        self.assertNotIn("p='evaluation_examples", body)
        steps = flow['jobs']['smoke']['steps']
        account = next(step for step in steps if step.get('name', '').startswith('Account usage'))
        self.assertEqual(account['if'], 'always()')

    def test_free_lane_and_vendor_blobs_unchanged(self):
        paths = ['certification/g3-osworld-arbm-agent.py',
                 '.github/workflows/osworld-g3-smoke-v2.yml',
                 '.github/workflows/osworld-g3-smoke.yml',
                 '.github/workflows/osworld-g3-model-probe.yml',
                 'certification/vendor-gemini-agent.py',
                 'certification/vendor-gemini-action-parser.py']
        paths.extend(str(p.relative_to(ROOT)).replace('\\', '/') for p in
                     (ROOT / 'certification/g3-computer-use-snapshot').glob('*.mjs'))
        for path in paths:
            with self.subTest(path=path):
                baseline = subprocess.check_output(['git', 'show', f'{BASELINE}:{path}'], cwd=ROOT)
                actual = (ROOT / path).read_bytes().replace(b'\r\n', b'\n')
                self.assertEqual(actual, baseline.replace(b'\r\n', b'\n'))


if __name__ == '__main__':
    unittest.main()
