import unittest

from arbm091.wps_observer import _coverstat1_repair_decision


def state(text="$2.8M", geometry=None, *, extra=None):
    geometry=geometry or {"x":8339327,"y":3355848,"w":2560320,"h":219456}
    rows=[{"id":16,"name":"CoverStatValue_1","text":text,"geometry":geometry}]
    if extra is not None:
        rows.append(extra)
    return {"deck_slide_shapes":{"1":rows}}


class CoverStat1GeometryDecisionTests(unittest.TestCase):
    def test_exact_text_and_geometry_pass(self):
        self.assertEqual(_coverstat1_repair_decision(state()),"PASS")

    def test_height_drift_requests_surgical_repair(self):
        ws=state(geometry={"x":8339327,"y":3355848,"w":2560320,"h":414020})
        self.assertEqual(_coverstat1_repair_decision(ws),"REPAIR_HEIGHT")

    def test_x_drift_fails_closed(self):
        ws=state(geometry={"x":8339328,"y":3355848,"w":2560320,"h":414020})
        self.assertEqual(_coverstat1_repair_decision(ws),"FAIL_CLOSED")

    def test_y_drift_fails_closed(self):
        ws=state(geometry={"x":8339327,"y":3355849,"w":2560320,"h":414020})
        self.assertEqual(_coverstat1_repair_decision(ws),"FAIL_CLOSED")

    def test_width_drift_fails_closed(self):
        ws=state(geometry={"x":8339327,"y":3355848,"w":2560321,"h":414020})
        self.assertEqual(_coverstat1_repair_decision(ws),"FAIL_CLOSED")

    def test_nonpositive_height_fails_closed(self):
        ws=state(geometry={"x":8339327,"y":3355848,"w":2560320,"h":0})
        self.assertEqual(_coverstat1_repair_decision(ws),"FAIL_CLOSED")

    def test_wrong_text_does_not_authorize_geometry_mutation(self):
        ws=state(text="$2.8MM",geometry={"x":8339327,"y":3355848,"w":2560320,"h":414020})
        self.assertEqual(_coverstat1_repair_decision(ws),"NOOP")

    def test_unrelated_sibling_does_not_change_target_decision(self):
        sibling={"id":99,"name":"Sibling","text":"keep","geometry":{"x":1,"y":2,"w":3,"h":4}}
        self.assertEqual(_coverstat1_repair_decision(state(extra=sibling)),"PASS")

    def test_duplicate_target_fails_to_authorize_repair(self):
        ws=state()
        ws["deck_slide_shapes"]["1"].append(dict(ws["deck_slide_shapes"]["1"][0]))
        self.assertEqual(_coverstat1_repair_decision(ws),"NOOP")


if __name__=="__main__":
    unittest.main()
