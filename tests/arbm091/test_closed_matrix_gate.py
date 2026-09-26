import unittest
from pathlib import Path

from arbm091.closed_matrix import assert_closed_matrix, matrix_rows


class Task091ClosedMatrixTests(unittest.TestCase):
    def test_closed_matrix_is_exactly_75_plus_1(self):
        summary=assert_closed_matrix()
        self.assertEqual(summary["transactions"],75)
        self.assertEqual(summary["mutations"],73)
        self.assertEqual(summary["preservations"],2)
        self.assertEqual(summary["section_e"],1)
        self.assertEqual(summary["preservation_ids"],["T025","T068"])

    def test_matrix_has_no_unclassified_lane(self):
        rows=matrix_rows()
        self.assertEqual(len(rows),75)
        self.assertEqual({row["mode"] for row in rows},{"mutate","preserve"})
        self.assertEqual(len({row["id"] for row in rows}),75)

    def test_workflow_has_matrix_preflight_and_no_historical_metagate(self):
        text=Path(".github/workflows/arbm-091-clean-proof.yml").read_text(encoding="utf-8")
        self.assertIn("matrix-preflight:",text)
        self.assertIn("TASK091_CLOSED_MATRIX_75_PLUS_1=PASS",text)
        self.assertIn("cancel-in-progress: false",text)
        self.assertNotIn("Verify clean history and exact changed-file scope",text)
        self.assertNotIn('elif [[ "$current_parent"',text)
        focal=text.split("  focal-091:",1)[1].split("  final-certification:",1)[0]
        self.assertIn("- matrix-preflight",focal)

    def test_final_board_requires_matrix_preflight(self):
        text=Path("scripts/arbm091/final_certification_board.py").read_text(encoding="utf-8")
        self.assertIn('"matrix-preflight"',text)


if __name__=="__main__":
    unittest.main()
