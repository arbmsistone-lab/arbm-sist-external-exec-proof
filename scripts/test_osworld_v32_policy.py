import unittest
from osworld_v32_policy import DecisionKind, extract_state, enforce_policy, classify_capacity


class TestV32Policy(unittest.TestCase):
    def test_background_file_not_foreground_proof(self):
        state = extract_state("Google Chrome", "label\tdegree_audit_report.pdf\nlabel\tSyllabus-CS-4Y.pdf")
        self.assertIn("degree_audit_report.pdf", state.background_elements)
        self.assertNotIn("degree_audit_report.pdf", state.foreground_visible)
        with self.assertRaisesRegex(ValueError, "NOOP_REQUIRES_FOREGROUND_PROOF"):
            enforce_policy(state, {"kind":"NOOP_VERIFIED","checkpoint":{"visible_text":"degree_audit_report.pdf"}})

    def test_desktop_file_can_prove_noop(self):
        state = extract_state("Desktop", "label\tdegree_audit_report.pdf")
        result = enforce_policy(state, {"kind":"NOOP_VERIFIED","checkpoint":{"visible_text":"degree_audit_report.pdf"}})
        self.assertEqual(result["kind"], DecisionKind.NOOP_VERIFIED.value)

    def test_open_archive_locks_context(self):
        state = extract_state("Archive Manager", "title filter.zip\nlabel city.zip")
        with self.assertRaisesRegex(ValueError, "SOURCE_CONTEXT_LOCKED"):
            enforce_policy(state, {"kind":"EXEC","command":"pyautogui.hotkey('ctrl', 'win', 'd')","checkpoint":{"application":"Desktop"}})

    def test_completed_archive_allows_transition(self):
        milestones=[{"name":"filter.zip read complete","verification":"verified"}]
        state = extract_state("Archive Manager", "title filter.zip", milestones)
        result = enforce_policy(state, {"kind":"EXEC","command":"pyautogui.hotkey('ctrl', 'win', 'd')","checkpoint":{"application":"Desktop"}})
        self.assertEqual(result["kind"], DecisionKind.EXEC.value)

    def test_capacity_is_not_cognitive_wait(self):
        self.assertEqual(classify_capacity(False), DecisionKind.HOLD_CAPACITY)
        self.assertEqual(classify_capacity(True), DecisionKind.EXEC)

    def test_finish_blocked_until_prerequisites_complete(self):
        state = extract_state("Archive Manager", "title filter.zip")
        with self.assertRaisesRegex(ValueError, "FINISH_WITH_UNMET_PREREQUISITES"):
            enforce_policy(state, {"kind":"FINISH_CANDIDATE"})


if __name__ == "__main__":
    unittest.main()

class TestLegacyBridge(unittest.TestCase):
    def test_wait_background_is_rejected(self):
        from osworld_v32_policy import decision_from_agent
        state = extract_state("Google Chrome", "label\tdegree_audit_report.pdf")
        with self.assertRaisesRegex(ValueError, "NOOP_REQUIRES_FOREGROUND_PROOF"):
            decision_from_agent({"action":"wait","checkpoint":{"visible_text":"degree_audit_report.pdf"}}, state)

    def test_wait_foreground_becomes_verified_noop(self):
        from osworld_v32_policy import decision_from_agent
        state = extract_state("Desktop", "label\tdegree_audit_report.pdf")
        result = decision_from_agent({"action":"wait","checkpoint":{"visible_text":"degree_audit_report.pdf"}}, state)
        self.assertEqual(result["kind"], DecisionKind.NOOP_VERIFIED.value)

    def test_capacity_overrides_agent_output(self):
        from osworld_v32_policy import decision_from_agent
        state = extract_state("Desktop", "label\tx.pdf")
        result = decision_from_agent({"action":"exec","command":"pyautogui.press('enter')"}, state, provider_available=False)
        self.assertEqual(result["kind"], DecisionKind.HOLD_CAPACITY.value)
