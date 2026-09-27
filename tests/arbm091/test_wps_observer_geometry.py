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

    def test_summary_nrr_completed_height_drift_requests_repair(self):
        ws={"deck_slide_shapes":{
            "2":[row(20,"SummaryNrr_Value","104%",
                     {"x":3227832,"y":1810512,"w":1837944,"h":460375})]
        }}
        self.assertEqual(
            dict(_coverstat_family_repair_decisions(ws))[(2,20,"SummaryNrr_Value")],
            "REPAIR_HEIGHT",
        )

    def test_summary_nrr_exact_geometry_passes(self):
        ws={"deck_slide_shapes":{
            "2":[row(20,"SummaryNrr_Value","104%",
                     {"x":3227832,"y":1810512,"w":1837944,"h":347472})]
        }}
        self.assertEqual(
            dict(_coverstat_family_repair_decisions(ws))[(2,20,"SummaryNrr_Value")],
            "PASS",
        )

    def test_summary_nrr_wrong_text_never_authorizes_repair(self):
        ws={"deck_slide_shapes":{
            "2":[row(20,"SummaryNrr_Value","112%",
                     {"x":3227832,"y":1810512,"w":1837944,"h":460375})]
        }}
        self.assertEqual(
            dict(_coverstat_family_repair_decisions(ws))[(2,20,"SummaryNrr_Value")],
            "NOOP",
        )

    def test_summary_nrr_nonheight_drift_fails_closed(self):
        ws={"deck_slide_shapes":{
            "2":[row(20,"SummaryNrr_Value","104%",
                     {"x":3227833,"y":1810512,"w":1837944,"h":460375})]
        }}
        self.assertEqual(
            dict(_coverstat_family_repair_decisions(ws))[(2,20,"SummaryNrr_Value")],
            "FAIL_CLOSED",
        )

    def test_missing_registered_member_fails_closed(self):
        ws=state(
            row(13,"CoverStatValue_0","$40.9M",{"x":8339327,"y":2167128,"w":2560320,"h":219456}),
            row(16,"CoverStatValue_1","$2.8M",{"x":8339327,"y":3355848,"w":2560320,"h":219456}),
        )
        self.assertEqual(dict(_coverstat_family_repair_decisions(ws))[(1,19,"CoverStatValue_2")],"FAIL_CLOSED")


    def test_summaryrunway_guest_payload_transports_actual_geometry(self):
        from pathlib import Path
        source = Path("scripts/arbm091/wps_observer.py").read_text(encoding="utf-8")
        self.assertIn(
            "expected_geom=tuple(cfg['expected']); actual=tuple(cfg['actual'])",
            source,
        )
        self.assertIn(
            "cfg=json.dumps({'path':path,'expected':list(expected),'actual':list(actual)}",
            source,
        )
        self.assertIn("'geometry_before':list(actual)", source)



    def test_summaryrunway_noop_contract_is_explicit(self):
        from pathlib import Path
        source = Path("scripts/arbm091/wps_observer.py").read_text(encoding="utf-8")
        self.assertIn("if actual==expected:", source)
        self.assertIn("'action':'NOOP'", source)
        self.assertIn("'geometry_after':list(expected_geom)", source)

    def test_summaryburn_recurring_suffix_repair_accepts_already_correct_28m_before(self):
        from pathlib import Path
        source = Path("scripts/arbm091/wps_observer.py").read_text(encoding="utf-8")
        self.assertIn("str(before_shape.get('text') or '') in ('$2.6M','$2.8M')", source)
        self.assertIn("str(burn_before.get('text') or '') in ('$2.6M','$2.8M')", source)

    def test_summaryburn_repair_remains_exact_negative_guard(self):
        from pathlib import Path
        source = Path("scripts/arbm091/wps_observer.py").read_text(encoding="utf-8")
        self.assertIn("str(persisted_shape.get('text') or '')=='$2.8MM'", source)
        self.assertIn("shape.count(b'$2.8MM')!=1", source)
        self.assertIn("shape.replace(b'$2.8MM',b'$2.8M',1)", source)


if __name__=="__main__":
    unittest.main()
