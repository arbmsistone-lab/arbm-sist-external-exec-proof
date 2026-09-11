import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class FreeWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / '.github/workflows/osworld-g3-free-smoke-v1.yml').read_text()
        self.data = yaml.safe_load(self.text)
        self.steps = self.data['jobs']['smoke']['steps']

    def test_admission_precedes_all_heavy_steps(self):
        names = [s['name'] for s in self.steps]
        probe = names.index('Prove FREE model contract before VM')
        for name in ('Prepare remote KVM runner', 'Checkout pinned OSWorld', 'Pin runtime and official VM'):
            self.assertLess(probe, names.index(name))
        self.assertIn('g3-free-cert-lane-20260910', self.data['jobs']['smoke']['if'])
        self.assertEqual(self.data['jobs']['smoke']['env']['ZERO_SPEND'], 'true')
        self.assertEqual(self.data['jobs']['smoke']['env']['HEAVY_LOCAL'], '0')

    def test_benchmark_pins_and_official_execution_preserved(self):
        for value in ('d578d2d4e0dc82b43e270fdaa7fa89d9708cd154', 'v2026.08.08',
                      'eb737ae70b49849e24af407de6a518439a23de05a8497096a948334ce0a909aa',
                      '--action_space pyautogui --observation_type screenshot', '--max_steps 100'):
            self.assertIn(value, self.text)
        self.assertIn('official_inputs_unchanged', self.text)

    def test_no_paid_secret_no_automatic_push_run(self):
        triggers = self.data.get('on', self.data.get(True))
        self.assertNotIn('push', triggers)
        self.assertNotIn('GEMINI_G3_PAID_CERT_KEY', self.text)
        self.assertNotIn('--model dots-studio/dots-3-note-preview:free', self.text)
        self.assertIn('--model "$FREE_MODEL_PATH"', self.text)

    def test_always_capture_and_reconcile_evidence(self):
        for name in ('Reconcile FREE journals after process exit', 'Package evidence independently of result filenames', 'Upload smoke evidence'):
            step = next(s for s in self.steps if s['name'] == name)
            self.assertEqual(step['if'], 'always()')
        upload = self.steps[-1]
        self.assertEqual(upload['with']['path'], 'free-artifacts')
        self.assertIn('official-trajectory.tar.gz', self.text)

    def test_embedded_python_compiles(self):
        import re
        for step in self.steps:
            script = step.get('run', '')
            for match in re.finditer(r"<<'(PY\w*)'\n(.*?)\n\1", script, re.S):
                compile(match.group(2), step['name'], 'exec')


if __name__ == '__main__':
    unittest.main()
