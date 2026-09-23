import copy
import unittest

from arbm091.semantic_transaction import (
    SemanticTransactionError,
    assert_roundtrip,
    expected_targets_for_pair,
    normalize_deck,
    resolve_target,
    verify_exact_text_transaction,
    validate_transaction_contract,
)


def shape(shape_id,name,text,x=100,y=100,w=100,h=40):
    return {"id":shape_id,"name":name,"text":text,"kind":"shape",
            "geometry":{"x":x,"y":y,"w":w,"h":h}}


def cell(frame_id,row,col,name,text,x=100,y=100,w=100,h=40):
    return {"id":-(frame_id*1000000+row*1000+col+1),"name":name,"text":text,
            "kind":"table-cell","frame_id":frame_id,"row":row,"col":col,
            "geometry":{"x":x,"y":y,"w":w,"h":h}}


def deck():
    return {
        "deck_slide_shapes":{
            "1":[shape(6,"CoverArr","$42.8M",100,100)],
            "2":[shape(7,"SummaryArr","$42.8M",200,100)],
            "3":[cell(12,1,2,"Table 12#r1c2","$42.8M",300,100),
                 cell(12,5,2,"Table 12#r5c2","2",300,300)],
            "12":[cell(9,6,5,"Appendix#r6c5","2",700,600)],
        },
        # Explicitly irrelevant raster/caret fields: oracle must ignore them.
        "screen":[0,0,1920,1080],
        "zoom":175,
        "caret_x":9999,
        "ink_left":1,
        "caret":{"bbox":[999,0,1,20],"proven":False},
    }


class SemanticTransactionTests(unittest.TestCase):
    def test_caret_zoom_and_raster_fields_have_zero_decision_power(self):
        a=deck()
        b=copy.deepcopy(a)
        b["screen"]=[0,0,3840,2160]
        b["zoom"]=67
        b["caret_x"]=-400
        b["ink_left"]=4000
        b["caret"]={"bbox":[1,1,4,35],"proven":True}
        self.assertEqual(normalize_deck(a),normalize_deck(b))
        self.assertEqual(
            resolve_target(a,slide=3,old="$42.8M")["key"],
            resolve_target(b,slide=3,old="$42.8M")["key"],
        )

    def test_font_hinting_antialiasing_and_ink_left_are_not_semantic_inputs(self):
        a=deck()
        b=copy.deepcopy(a)
        a.update(hinting="A",antialiasing="subpixel",ink_left=1)
        b.update(hinting="B",antialiasing="grayscale",ink_left=9999)
        self.assertEqual(normalize_deck(a),normalize_deck(b))

    def test_missing_target_fails_closed(self):
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_TARGET_MISSING"):
            resolve_target(deck(),slide=3,old="does-not-exist")

    def test_ambiguous_target_without_structural_hint_fails_closed(self):
        d=deck()
        d["deck_slide_shapes"]["3"].append(
            cell(99,1,2,"Other#r1c2","$42.8M",800,100))
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_TARGET_AMBIGUOUS"):
            resolve_target(d,slide=3,old="$42.8M")

    def test_duplicate_old_text_outside_authorized_set_blocks_global_replace(self):
        d=deck()
        spatial=((3,350,120,"2","3"),)
        contract=expected_targets_for_pair(d,spatial,"2","3")
        self.assertFalse(contract["global_exact_replace_safe"])
        self.assertEqual(len(contract["keys"]),1)
        self.assertEqual(len(contract["all_exact_occurrences"]),2)

    def test_exact_unique_semantic_change_passes(self):
        before=deck()
        target=resolve_target(before,slide=3,old="$42.8M")["key"]
        after=copy.deepcopy(before)
        after["deck_slide_shapes"]["3"][0]["text"]="$40.9M"
        verdict=verify_exact_text_transaction(before,after,[target],"$40.9M")
        self.assertEqual(verdict["status"],"PASS")
        self.assertEqual(verdict["changed_semantic_targets"],1)
        self.assertEqual(verdict["collateral_diff"],[])
        self.assertEqual(assert_roundtrip(after,[target],"$40.9M")["status"],"PASS")

    def test_sibling_collateral_change_fails(self):
        before=deck()
        target=resolve_target(before,slide=3,old="$42.8M")["key"]
        after=copy.deepcopy(before)
        after["deck_slide_shapes"]["3"][0]["text"]="$40.9M"
        after["deck_slide_shapes"]["3"][1]["text"]="3"
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_SEMANTIC_DIFF_MISMATCH"):
            verify_exact_text_transaction(before,after,[target],"$40.9M")

    def test_unexpected_geometry_change_fails(self):
        before=deck()
        target=resolve_target(before,slide=3,old="$42.8M")["key"]
        after=copy.deepcopy(before)
        after["deck_slide_shapes"]["3"][0]["text"]="$40.9M"
        after["deck_slide_shapes"]["3"][0]["geometry"]["w"]+=1
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_SEMANTIC_DIFF_MISMATCH"):
            verify_exact_text_transaction(before,after,[target],"$40.9M")

    def test_unexpected_slide_relationship_change_fails_closed(self):
        before=deck()
        before["deck_slide_relationships"]={"3":[{
            "type":"slideLayout","target":"ppt/slideLayouts/slideLayout1.xml","target_mode":""
        }]}
        target=resolve_target(before,slide=3,old="$42.8M")["key"]
        after=copy.deepcopy(before)
        after["deck_slide_shapes"]["3"][0]["text"]="$40.9M"
        after["deck_slide_relationships"]["3"].append({
            "type":"hyperlink","target":"https://example.invalid","target_mode":"External"
        })
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_SEMANTIC_DIFF_MISMATCH"):
            verify_exact_text_transaction(before,after,[target],"$40.9M")

    def test_save_without_persistence_fails_roundtrip(self):
        before=deck()
        target=resolve_target(before,slide=3,old="$42.8M")["key"]
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_ROUNDTRIP_VALUE_MISMATCH"):
            assert_roundtrip(before,[target],"$40.9M")

    def test_adversarial_collateral_rejected_then_clean_passes(self):
        before=deck()
        target=resolve_target(before,slide=3,old="$42.8M")["key"]
        bad=copy.deepcopy(before)
        bad["deck_slide_shapes"]["3"][0]["text"]="$40.9M"
        bad["deck_slide_shapes"]["12"][0]["text"]="CORRUPT"
        with self.assertRaises(SemanticTransactionError):
            verify_exact_text_transaction(before,bad,[target],"$40.9M")
        good=copy.deepcopy(before)
        good["deck_slide_shapes"]["3"][0]["text"]="$40.9M"
        self.assertEqual(
            verify_exact_text_transaction(before,good,[target],"$40.9M")["status"],
            "PASS",
        )

    def test_contained_shape_target_is_valid_semantic_contract(self):
        d=deck()
        d["deck_slide_shapes"]["1"][0]["text"]="H2 Operating Committee Pack\nGrowth Plan Draft"
        resolved=resolve_target(d,slide=1,old="Growth Plan Draft")
        verdict=validate_transaction_contract(
            d,resolved["key"],"Growth Plan Draft",
            "H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline")
        self.assertEqual(verdict["status"],"PASS")
        self.assertTrue(verdict["target_unique"])
        self.assertTrue(verdict["mutation_authorized"])

    def test_unique_contained_shape_text_resolves_without_raster_authority(self):
        d=deck()
        d["deck_slide_shapes"]["1"][0]["text"]="Northstar Cloud\nPlanning posture: accelerate growth through H2 scale-up"
        resolved=resolve_target(
            d,slide=1,old="Planning posture: accelerate growth through H2 scale-up")
        self.assertEqual(resolved["match_kind"],"contained")
        self.assertEqual(resolved["row"]["name"],"CoverArr")

    def test_exact_match_has_priority_over_contained_match(self):
        d=deck()
        d["deck_slide_shapes"]["1"].append(
            shape(9,"Contained","prefix $42.8M suffix",500,100))
        resolved=resolve_target(d,slide=1,old="$42.8M")
        self.assertEqual(resolved["match_kind"],"exact")
        self.assertEqual(resolved["row"]["name"],"CoverArr")


if __name__=="__main__":
    unittest.main()
