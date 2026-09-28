import unittest
from arbm_senior_elite_board import review_action

SHA = "a" * 40
COMMAND = "pyautogui.click(983, 471)"

def state(stage="table-cell-enter-issued", with_evidence=True):
    pending = {
        "stage": stage,
        "shape_kind": "table-cell",
        "target": {"cx": 983, "cy": 471},
    }
    if with_evidence:
        pending.update({
            "table_selected_screenshot_sha256": "b" * 64,
            "table_selected_target_visual_sha256": "c" * 64,
            "table_selected_sibling_visual_sha256": "d" * 64,
        })
    return {"task091_specialist": {"owned": True, "handoff": False, "pending_edit": pending}}

def action():
    return {
        "action": "exec",
        "command": COMMAND,
        "target": {"source": "task091-pptx-canonical"},
        "specialist_phase": "enter-table-cell-caret-candidate",
    }

class SeniorEliteTask091CaretAdmissionTests(unittest.TestCase):
    def review(self, no_progress, s=None, recent=None):
        return review_action(
            action(), task_id="091", source="task091-specialist",
            state=s if s is not None else state(),
            verifier={"no_progress": no_progress},
            recent_commands=recent if recent is not None else [COMMAND],
            zero_spend_mode="HARD", github_sha=SHA,
        )

    def test_evidence_proven_second_click_is_admitted_at_observed_counter(self):
        result = self.review(2)
        self.assertTrue(result["allow"], result)

    def test_first_no_progress_counter_does_not_bypass_repeat_guard(self):
        result = self.review(1)
        self.assertFalse(result["allow"], result)
        self.assertIn("anti_repetition", result["failed"])

    def test_third_repeat_is_blocked(self):
        result = self.review(3)
        self.assertFalse(result["allow"], result)
        self.assertIn("anti_repetition", result["failed"])

    def test_missing_visual_evidence_is_blocked(self):
        result = self.review(2, s=state(with_evidence=False))
        self.assertFalse(result["allow"], result)
        self.assertIn("anti_repetition", result["failed"])

    def test_wrong_stage_is_blocked(self):
        result = self.review(2, s=state(stage="table-select-issued"))
        self.assertFalse(result["allow"], result)
        self.assertIn("anti_repetition", result["failed"])

if __name__ == "__main__":
    unittest.main()
