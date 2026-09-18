import unittest

import osworld_control as control


class WPSForegroundRegressionTests(unittest.TestCase):
    def test_wps_panel_drops_stale_background_web_tree(self):
        raw=(
            "push-button\tMinimise\tMinimise\t\t\t(1802, 27)\t(30, 35)\n"
            "document-web\tMailHub\t\"\"\t\t\t(70, 114)\t(1850, 966)\n"
            "section\t\tH2 Rebaseline Directive: Operating Committee Pack\t\t\t(626, 299)\t(976, 20)\n"
            "menu\tWPS 2019\t\"\"\t\t\t(99, 0)\t(124, 27)\n"
            "menu\tSystem\t\"\"\t\t\t(1814, 0)\t(106, 27)\n"
            "push-button\tGoogle Chrome\t\"\"\t\t\t(0, 25)\t(70, 64)\n"
            "push-button\tWPS Presentation\t\"\"\t\t\t(0, 844)\t(70, 64)"
        )
        focused,active=control.foreground_context(raw)
        self.assertEqual(active,"WPS 2019")
        self.assertNotIn("document-web\tMailHub",focused)
        self.assertNotIn("H2 Rebaseline Directive",focused)
        self.assertIn("menu\tWPS 2019",focused)

    def test_wps_visual_modal_dismiss_is_repaired_to_escape(self):
        action={
            "action":"exec",
            "command":"pyautogui.click(775, 416)",
            "plan":"Close the foreground WPS System Check modal.",
            "summary":"Close the blocking System Check dialog.",
            "expected_change":"The modal should close.",
            "observed_facts":[{"quote":"System Check"},{"quote":"Close"}],
            "checkpoint":{"name":"modal_closed","application":"WPS 2019","visible_text":"System Check dialog closed"},
        }
        out=control.ground_action(action,"WPS 2019","",[])
        self.assertEqual(out["command"],"pyautogui.press('esc')")
        self.assertIn("WPS modal-dismiss",out.get("compiler_note",""))

    def test_after_two_stalled_escapes_uses_explicit_visual_close_target(self):
        action={
            "action":"exec",
            "command":"pyautogui.click(774, 416)",
            "plan":"Close the foreground System Check dialog.",
            "summary":"Close the visible WPS dialog.",
            "verification":"The dialog remains foreground and Close is visible.",
            "expected_change":"The System Check dialog should disappear.",
            "observed_facts":[{"quote":"System Check"},{"quote":"Close"}],
            "checkpoint":{"name":"system_check_dismissed","application":"WPS Presentation","visible_text":"Slide 1 / 13"},
        }
        out=control.ground_action(
            action,"WPS 2019","",[],
            verifier_result={"reason":"action_no_progress","tree_changed":False,"visual_changed":False},
            recent_commands=["pyautogui.press('esc')","pyautogui.press('esc')"])
        self.assertEqual(out["command"],"pyautogui.click(774, 416)")
        self.assertEqual(out["target"]["source"],"screenshot")
        self.assertEqual(out["target"]["label"],"Close")
        self.assertIn("two bounded Escape",out.get("compiler_note",""))

    def test_after_two_stalled_escapes_without_named_control_remains_fail_closed(self):
        action={
            "action":"exec",
            "command":"pyautogui.click(774, 416)",
            "plan":"Dismiss the foreground System Check dialog.",
            "summary":"Dismiss the visible dialog.",
            "observed_facts":[{"quote":"System Check"}],
        }
        with self.assertRaisesRegex(ValueError,"POINTER_TARGET_REQUIRED"):
            control.ground_action(
                action,"WPS 2019","",[],
                verifier_result={"reason":"action_no_progress","tree_changed":False,"visual_changed":False},
                recent_commands=["pyautogui.press('esc')","pyautogui.press('esc')"])

    def test_bounded_second_escape_requires_verified_ui_change(self):
        action={
            "action":"exec",
            "command":"pyautogui.press('esc')",
            "compiler_note":"Replaced ungrounded WPS modal-dismiss pointer with deterministic Escape.",
        }
        self.assertTrue(control.allow_bounded_wps_escape_repeat(
            action,"WPS 2019",{"tree_changed":True,"visual_changed":False},["pyautogui.press('esc')"]))
        self.assertFalse(control.allow_bounded_wps_escape_repeat(
            action,"WPS 2019",{"tree_changed":False,"visual_changed":False},["pyautogui.press('esc')"]))
        self.assertFalse(control.allow_bounded_wps_escape_repeat(
            action,"WPS 2019",{"tree_changed":True,"visual_changed":False},
            ["pyautogui.press('esc')","pyautogui.press('esc')"]))

    def test_bounded_modal_close_repeat_allows_exactly_one_focus_retry(self):
        action={
            "action":"exec",
            "command":"pyautogui.click(774, 416)",
            "target":{"source":"screenshot","label":"Close"},
            "compiler_note":"After two bounded Escape attempts, preserved the single visual pointer using the explicitly observed modal control label.",
        }
        stalled={"reason":"action_no_progress","tree_changed":False,"visual_changed":False}
        self.assertTrue(control.allow_bounded_wps_modal_close_repeat(
            action,"WPS 2019",stalled,["pyautogui.click(774, 416)"]))
        self.assertFalse(control.allow_bounded_wps_modal_close_repeat(
            action,"WPS 2019",stalled,["pyautogui.click(774, 416)","pyautogui.click(774, 416)"]))

    def test_bounded_modal_close_repeat_rejects_unrelated_pointer(self):
        action={
            "action":"exec",
            "command":"pyautogui.click(774, 416)",
            "target":{"source":"screenshot","label":"Open"},
            "compiler_note":"After two bounded Escape attempts, preserved the single visual pointer using the explicitly observed modal control label.",
        }
        stalled={"reason":"action_no_progress","tree_changed":False,"visual_changed":False}
        self.assertFalse(control.allow_bounded_wps_modal_close_repeat(
            action,"WPS 2019",stalled,["pyautogui.click(774, 416)"]))

    def test_bounded_escape_does_not_apply_without_modal_repair_proof(self):
        action={"action":"exec","command":"pyautogui.press('esc')"}
        self.assertFalse(control.allow_bounded_wps_escape_repeat(
            action,"WPS 2019",{"tree_changed":True},["pyautogui.press('esc')"]))

    def test_unrelated_wps_pointer_without_target_remains_fail_closed(self):
        action={
            "action":"exec",
            "command":"pyautogui.click(775, 416)",
            "plan":"Open the workbook row.",
            "summary":"Open the selected source item.",
        }
        with self.assertRaisesRegex(ValueError,"POINTER_TARGET_REQUIRED"):
            control.ground_action(action,"WPS 2019","",[])


if __name__=="__main__":
    unittest.main()
