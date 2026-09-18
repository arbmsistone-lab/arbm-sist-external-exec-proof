"""Regression for the real workflow's literal task identity and startup guard."""
from __future__ import annotations
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import yaml
from arbm091.wps_observer import install

WORKFLOW = Path('.github/workflows/arbm-091-clean-proof.yml')

def child(node, name):
    return next(value for key, value in node.value if key.value == name)

class WorkflowRuntimeContractTests(unittest.TestCase):
    def test_task_id_has_explicit_yaml_string_style(self):
        node = yaml.compose(WORKFLOW.read_text())
        for key in ('jobs', 'focal-091', 'env', 'TASK_ID'):
            node = child(node, key)
        self.assertEqual(node.value, '091')
        self.assertEqual(node.tag, 'tag:yaml.org,2002:str')
        self.assertIn(node.style, ("'", '"'))

    def test_task_id_value_is_exact(self):
        data = yaml.safe_load(WORKFLOW.read_text())
        self.assertEqual(data['jobs']['focal-091']['env']['TASK_ID'], '091')

    def test_literal_environment_guard_precedes_runtime_preparation(self):
        steps = yaml.safe_load(WORKFLOW.read_text())['jobs']['focal-091']['steps']
        names = [s.get('name', '') for s in steps]
        guard = 'Validate literal task identity before runtime preparation'
        self.assertIn(guard, names)
        self.assertLess(names.index(guard), names.index('Prepare pinned shim runtime'))
        self.assertIn('test "$TASK_ID" = \'091\'', steps[names.index(guard)]['run'])
        self.assertNotIn('continue-on-error', steps[names.index(guard)])

    def test_pinned_observer_import_precedes_vm_download(self):
        steps = yaml.safe_load(WORKFLOW.read_text())['jobs']['focal-091']['steps']
        names = [s.get('name', '') for s in steps]
        check = 'Validate observer import in pinned upstream runtime before VM'
        self.assertIn(check, names)
        self.assertLess(names.index(check), names.index('Download pinned official VM'))
        self.assertGreater(names.index(check), names.index('Apply exact upstream runtime patches'))
        self.assertNotIn('continue-on-error', steps[names.index(check)])

class ObserverStartupContractTests(unittest.TestCase):
    def make_environment(self):
        class Environment:
            def step(self, action, pause=2):
                raise AssertionError('startup check must not execute a GUI action')
        return Environment

    def environment(self):
        return {'RUNNER_ENVIRONMENT': 'github-hosted', 'ZERO_SPEND_MODE': 'HARD', 'TASK_ID': '091'}

    def test_exact_remote_zero_spend_task_installs_without_gui_execution(self):
        environment = self.make_environment()
        original = environment.step
        with patch.dict(os.environ, self.environment(), clear=True):
            install(environment)
        self.assertTrue(environment._arbm091_observed)
        self.assertIsNot(environment.step, original)

    def test_duplicate_install_preserves_single_wrapper(self):
        environment = self.make_environment()
        with patch.dict(os.environ, self.environment(), clear=True):
            install(environment)
            first = environment.step
            install(environment)
        self.assertIs(environment.step, first)

    def test_noncanonical_and_wrong_task_ids_are_rejected(self):
        for value in ('91', '0091', '091 ', '090', ''):
            with self.subTest(task=value):
                env = self.environment()
                env['TASK_ID'] = value
                environment = self.make_environment()
                original = environment.step
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaisesRegex(ValueError, 'OBSERVER_REMOTE_ZERO_SPEND_TASK091_REQUIRED'):
                        install(environment)
                self.assertIs(environment.step, original)

    def test_nonfree_modes_are_rejected(self):
        for value in ('SOFT', 'PAID', ''):
            with self.subTest(mode=value):
                env = self.environment()
                env['ZERO_SPEND_MODE'] = value
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaisesRegex(ValueError, 'OBSERVER_REMOTE_ZERO_SPEND_TASK091_REQUIRED'):
                        install(self.make_environment())

    def test_local_and_unknown_runners_are_rejected(self):
        for value in ('self-hosted', 'local', ''):
            with self.subTest(runner=value):
                env = self.environment()
                env['RUNNER_ENVIRONMENT'] = value
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaisesRegex(ValueError, 'OBSERVER_REMOTE_ZERO_SPEND_TASK091_REQUIRED'):
                        install(self.make_environment())

    def test_missing_environment_is_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'OBSERVER_REMOTE_ZERO_SPEND_TASK091_REQUIRED'):
                install(self.make_environment())

if __name__ == '__main__':
    unittest.main()
