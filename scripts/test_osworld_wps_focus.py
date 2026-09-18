"""Unit tests are synthetic contracts, never official task-score evidence."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from osworld_wps_focus import APP, audit, focus_recovery, install, observed_app, validate_action


def row(role, label, x, y, w=60, h=24):
    return f'{role}\t{label}\t\t\t\t({x}, {y})\t({w}, {h})'


def scene(app='WPS Presentation'):
    return '\n'.join((row('menu', 'System', 0, 0), row('menu', app, 80, 0, 200),
                      row('frame', 'Deck - WPS Presentation', 72, 24, 1800, 1000),
                      row('push-button', 'Save', 120, 110),
                      row('push-button', 'Google Chrome', 5, 50, 60, 60),
                      row('push-button', 'WPS Presentation', 5, 130, 60, 60)))


def action(command="pyautogui.hotkey('ctrl', 's')", target=None):
    value = {'action': 'exec', 'command': command}
    if target is not None:
        value['target'] = target
    return value


class WPSFocusTests(unittest.TestCase):
    def test_exact_panel_is_required(self):
        self.assertEqual(observed_app(scene()), APP)
        with self.assertRaisesRegex(ValueError, 'UNPROVEN'):
            observed_app('The task says WPS Presentation')

    def test_chrome_title_is_not_wps(self):
        self.assertNotEqual(observed_app(scene('WPS Presentation - Google Chrome')), APP)

    def test_ambiguous_panels_fail_closed(self):
        with self.assertRaisesRegex(ValueError, 'AMBIGUOUS'):
            observed_app(scene()+'\n'+row('menu', 'Google Chrome', 400, 0))

    def test_canonical_prefix_only_is_explicitly_opt_in(self):
        text = 'ACTIVE APPLICATION (Ubuntu panel): WPS Presentation\n'
        with self.assertRaisesRegex(ValueError, 'UNPROVEN'):
            observed_app(text)
        self.assertEqual(observed_app(text, allow_canonical_prefix=True), APP)

    def test_recovery_uses_observed_geometry(self):
        value = focus_recovery(scene('Google Chrome'), 0)
        self.assertEqual(value['command'], 'pyautogui.click(35, 160)')
        self.assertEqual(value['target']['label'], 'WPS Presentation')

    def test_absent_or_ambiguous_launcher_fails(self):
        with self.assertRaisesRegex(ValueError, 'TARGET_UNPROVEN'):
            focus_recovery(row('menu', 'Google Chrome', 80, 0), 0)
        with self.assertRaisesRegex(ValueError, 'TARGET_UNPROVEN'):
            focus_recovery(scene()+'\n'+row('button', 'WPS Presentation', 500, 300), 0)

    def test_focus_attempts_are_bounded(self):
        with self.assertRaisesRegex(ValueError, 'EXHAUSTED'):
            focus_recovery(scene(), 2)

    def test_save_and_escape_are_not_context_switches(self):
        validate_action(action(), scene())
        validate_action(action("pyautogui.press('esc')"), scene())

    def test_foreground_mismatch_blocks_keyboard(self):
        with self.assertRaisesRegex(ValueError, 'FOREGROUND_REQUIRED'):
            validate_action(action(), scene('Google Chrome'))

    def test_context_switches_blocked(self):
        for command in ("pyautogui.hotkey('alt', 'tab')", "pyautogui.hotkey('alt', 'f4')",
                        "pyautogui.hotkey('ctrl', 'q')", "pyautogui.hotkey('ctrl', 'win', 'd')",
                        "pyautogui.keyDown('alt')", "pyautogui.press(['win', 'r'])"):
            with self.subTest(command=command), self.assertRaisesRegex(ValueError, 'CONTEXT_SWITCH'):
                validate_action(action(command), scene())

    def test_external_target_blocked(self):
        target = {'source': 'accessibility', 'label': 'Google Chrome', 'role': 'push-button'}
        with self.assertRaisesRegex(ValueError, 'EXTERNAL_TARGET'):
            validate_action(action('pyautogui.click(35, 80)', target), scene())

    def test_target_label_cannot_disguise_launcher_coordinates(self):
        target = {'source': 'screenshot', 'label': 'Save'}
        with self.assertRaisesRegex(ValueError, 'APPLICATION_CONTROL'):
            validate_action(action('pyautogui.click(35, 80)', target), scene())

    def test_absolute_coordinates_required(self):
        with self.assertRaisesRegex(ValueError, 'ABSOLUTE_POINTER'):
            validate_action(action('pyautogui.click()'), scene())

    def test_wps_accessibility_target_is_checked(self):
        target = {'source': 'accessibility', 'label': 'Save', 'role': 'push-button'}
        validate_action(action('pyautogui.click(150, 122)', target), scene())
        with self.assertRaisesRegex(ValueError, 'TARGET_UNPROVEN'):
            validate_action(action('pyautogui.click(800, 500)', target), scene())

    def test_background_browser_tree_not_promoted(self):
        target = {'source': 'accessibility', 'label': 'Save', 'role': 'push-button'}
        text = scene()+'\n'+row('document-web', 'MailHub', 70, 114, 1850, 966)
        with self.assertRaisesRegex(ValueError, 'BACKGROUND_WEB_TREE'):
            validate_action(action('pyautogui.click(150, 122)', target), text)

    def test_install_requires_explicit_strict_zero_spend(self):
        with patch.dict(os.environ, {'ARBM_STRICT_WPS': '0', 'ZERO_SPEND_MODE': 'HARD'}):
            with self.assertRaisesRegex(ValueError, 'STRICT_MODE'):
                install(SimpleNamespace(), SimpleNamespace())
        with patch.dict(os.environ, {'ARBM_STRICT_WPS': '1', 'ZERO_SPEND_MODE': 'OFF'}):
            with self.assertRaisesRegex(ValueError, 'ZERO_SPEND'):
                install(SimpleNamespace(), SimpleNamespace())

    def test_selector_preserved_but_unsafe_candidates_removed(self):
        options = [{'action': action()}, {'action': action("pyautogui.hotkey('alt', 'tab')")}]
        shim = SimpleNamespace(call_mesh=lambda messages: 'WAIT', ground_action=lambda value, *a, **kw: value)
        local = SimpleNamespace(_selector_candidates=lambda body, limit=18: options)
        with patch.dict(os.environ, {'ARBM_STRICT_WPS': '1', 'ZERO_SPEND_MODE': 'HARD'}):
            install(shim, local)
            installed = shim.call_mesh
            install(shim, local)
            self.assertIs(shim.call_mesh, installed)
            kept = local._selector_candidates({'active_application': 'WPS Presentation', 'observation': scene()})
            self.assertEqual(kept, options[:1])
            with self.assertRaisesRegex(ValueError, 'WPS_CONTEXT_REQUIRED'):
                local._selector_candidates({'active_application': 'Google Chrome', 'observation': scene('Google Chrome')})

    def test_audit_rejects_unadmitted_action(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'shim.jsonl'
            path.write_text(json.dumps({'status': 'ACTION_ISSUED', 'command': 'bad', 'step': 1})+'\n')
            with self.assertRaisesRegex(ValueError, 'WITHOUT_ADMISSION'):
                audit(path)

    def test_trace_pass_does_not_claim_official_score(self):
        command = action()['command']
        events = [dict(status='WPS_FOCUS_OBSERVED', active_application='WPS Presentation', step=0),
                  dict(status='STRICT_WPS_ACTION_ADMITTED', step=1, observation_sha256='a'*64,
                       command_sha256=hashlib.sha256(command.encode()).hexdigest()),
                  dict(status='ACTION_ISSUED', step=1, command=command)]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'shim.jsonl'
            path.write_text(''.join(json.dumps(e)+'\n' for e in events))
            result = audit(path)
            self.assertFalse(result['official_score_claimed'])
            self.assertEqual(result['status'], 'STRICT_WPS_TRACE_PASS')


if __name__ == '__main__':
    unittest.main()
