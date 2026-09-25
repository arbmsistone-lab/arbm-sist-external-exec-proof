import unittest

from arbm091.wps_observer import (
    _COVERSTAT_ATOMIC_REGISTRY,
    _coverstat_family_repair_decisions,
)


def row(shape_id,name,text,geometry):
    return {"id":shape_id,"name":name,"text":text,"geometry":geometry}


def state(*rows):
    return {"deck_slide_shapes":{"1":list(rows)}}


class CoverStatFamilyGeometryDecisionTests(unittest.TestCase):
    def test_registry_has_proven_family_members(self):
        self.assertEqual(_COVERSTAT_ATOMIC_REGISTRY[(1,13,"CoverStatValue_0")],
                         {"geometry":(8339327,2167128,2560320,219456),"completed_text":"$40.9M"})
        self.assertEqual(_COVERSTAT_ATOMIC_REGISTRY[(1,16,"CoverStatValue_1")]["geometry"],
                         (8339327,3355848,2560320,219456))
        self.assertEqual(_COVERSTAT_ATOMIC_REGISTRY[(1,19,"CoverStatValue_2")]["geometry"],
                         (8339327,4544568,2560320,219456))

    def test_completed_members_exact_pass(self):
        ws=state(
            row(16,"CoverStatValue_1","$2.8M",{"x":8339327,"y":3355848,"w":2560320,"h":219456}),
            row(19,"CoverStatValue_2","206",{"x":8339327,"y":4544568,"w":2560320,"h":219456}),
        )
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,16,"CoverStatValue_1")],"PASS")
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,19,"CoverStatValue_2")],"PASS")

    def test_value1_height_drift_requests_repair(self):
        ws=state(row(16,"CoverStatValue_1","$2.8M",{"x":8339327,"y":3355848,"w":2560320,"h":414020}))
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,16,"CoverStatValue_1")],"REPAIR_HEIGHT")

    def test_value2_height_drift_requests_repair(self):
        ws=state(row(19,"CoverStatValue_2","206",{"x":8339327,"y":4544568,"w":2560320,"h":414020}))
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,19,"CoverStatValue_2")],"REPAIR_HEIGHT")

    def test_arbitrary_positive_height_drift_requests_repair(self):
        ws=state(row(19,"CoverStatValue_2","206",{"x":8339327,"y":4544568,"w":2560320,"h":300000}))
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,19,"CoverStatValue_2")],"REPAIR_HEIGHT")

    def test_x_drift_fails_closed(self):
        ws=state(row(19,"CoverStatValue_2","206",{"x":8339328,"y":4544568,"w":2560320,"h":414020}))
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,19,"CoverStatValue_2")],"FAIL_CLOSED")

    def test_y_drift_fails_closed(self):
        ws=state(row(19,"CoverStatValue_2","206",{"x":8339327,"y":4544569,"w":2560320,"h":414020}))
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,19,"CoverStatValue_2")],"FAIL_CLOSED")

    def test_width_drift_fails_closed(self):
        ws=state(row(19,"CoverStatValue_2","206",{"x":8339327,"y":4544568,"w":2560321,"h":414020}))
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,19,"CoverStatValue_2")],"FAIL_CLOSED")

    def test_nonpositive_height_fails_closed(self):
        ws=state(row(19,"CoverStatValue_2","206",{"x":8339327,"y":4544568,"w":2560320,"h":0}))
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,19,"CoverStatValue_2")],"FAIL_CLOSED")

    def test_wrong_text_does_not_authorize_repair(self):
        ws=state(row(19,"CoverStatValue_2","214",{"x":8339327,"y":4544568,"w":2560320,"h":414020}))
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,19,"CoverStatValue_2")],"NOOP")

    def test_duplicate_completed_target_fails_closed(self):
        r=row(19,"CoverStatValue_2","206",{"x":8339327,"y":4544568,"w":2560320,"h":414020})
        ws=state(r,dict(r))
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,19,"CoverStatValue_2")],"FAIL_CLOSED")

    def test_unrelated_sibling_does_not_change_target_decision(self):
        ws=state(
            row(19,"CoverStatValue_2","206",{"x":8339327,"y":4544568,"w":2560320,"h":219456}),
            row(99,"Sibling","keep",{"x":1,"y":2,"w":3,"h":4}),
        )
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,19,"CoverStatValue_2")],"PASS")

    def test_value0_completed_height_drift_requests_repair(self):
        ws=state(row(13,"CoverStatValue_0","$40.9M",{"x":8339327,"y":2167128,"w":2560320,"h":414020}))
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,13,"CoverStatValue_0")],"REPAIR_HEIGHT")

    def test_unmutated_value0_wrong_text_is_not_repaired(self):
        ws=state(row(13,"CoverStatValue_0","$42.8M",{"x":8339327,"y":2167128,"w":2560320,"h":414020}))
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,13,"CoverStatValue_0")],"NOOP")

    def test_completed_family_is_rechecked_together_after_each_save(self):
        ws=state(
            row(13,"CoverStatValue_0","$40.9M",{"x":8339327,"y":2167128,"w":2560320,"h":414020}),
            row(16,"CoverStatValue_1","$2.8M",{"x":8339327,"y":3355848,"w":2560320,"h":219456}),
            row(19,"CoverStatValue_2","206",{"x":8339327,"y":4544568,"w":2560320,"h":219456}),
        )
        decisions=dict(_coverstat_family_repair_decisions(ws))
        self.assertEqual(decisions[(1,13,"CoverStatValue_0")],"REPAIR_HEIGHT")
        self.assertEqual(decisions[(1,16,"CoverStatValue_1")],"PASS")
        self.assertEqual(decisions[(1,19,"CoverStatValue_2")],"PASS")

    def test_missing_registered_member_fails_closed(self):
        ws=state(
            row(13,"CoverStatValue_0","$40.9M",{"x":8339327,"y":2167128,"w":2560320,"h":219456}),
            row(16,"CoverStatValue_1","$2.8M",{"x":8339327,"y":3355848,"w":2560320,"h":219456}),
        )
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,19,"CoverStatValue_2")],"FAIL_CLOSED")


if __name__=="__main__":
    unittest.main()
