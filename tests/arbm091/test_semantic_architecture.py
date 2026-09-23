"""Permanent anti-regression tests for the Task 091 semantic architecture."""
import copy
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from arbm091.semantic_transaction import (
    SemanticTransactionError,
    assert_roundtrip,
    normalize_deck,
    resolve_target,
    semantic_diff,
    verify_exact_text_transaction,
)
from arbm091.score_tracker import (
    SEMANTIC_REQUIRED_STATUSES,
    exact_result,
    verify_semantic_architecture,
)


def row(shape_id, name, text, x=100, y=100, kind="shape", frame_id=0, r=-1, c=-1):
    return {
        "id":shape_id,"name":name,"text":text,"kind":kind,
        "frame_id":frame_id,"row":r,"col":c,
        "geometry":{"x":x,"y":y,"w":120,"h":40},
        "font_sizes":[1800],"fill_rgb":"",
    }


def state(rows, sha="a"*64, relationships=None, **extra):
    value={
        "deck_slide_shapes":{"3":copy.deepcopy(rows)},
        "deck_slide_charts":{},
        "deck_slide_relationships":{"3":copy.deepcopy(relationships or [])},
        "deck_file":{"sha256":sha,"slide_size":{"w":12192000,"h":6858000}},
        "screen":[0,0,1920,1080],
        "window":{"bbox":[70,27,1850,1053],"title":"Operating_Committee_Rebaseline_Draft.pptx - WPS Presentation"},
        "active_slide":3,
    }
    value.update(extra)
    return value


class SemanticArchitectureTests(unittest.TestCase):
    def setUp(self):
        self.target=row(-12000002,"Table 12#r1c1","$42.8M",x=900,y=430,
                        kind="table-cell",frame_id=12,r=1,c=1)
        self.sibling=row(-12000003,"Table 12#r1c2","104%",x=1030,y=430,
                         kind="table-cell",frame_id=12,r=1,c=2)
        self.before=state([self.target,self.sibling])
        changed=copy.deepcopy(self.target); changed["text"]="$40.9M"
        self.after=state([changed,self.sibling],sha="b"*64)
        self.key=next(key for key,value in normalize_deck(self.before).items()
                      if value["text"]=="$42.8M")

    def test_A_caret_geometry_has_zero_decision_power(self):
        before=copy.deepcopy(self.before); after=copy.deepcopy(self.after)
        before.update(caret_x=1009,ink_left=956,zoom=80,blink_phase="visible")
        after.update(caret_x=-999,ink_left=4000,zoom=175,blink_phase="hidden")
        before["deck_slide_shapes"]["3"][0].update(caret_x=1009,ink_left=956)
        after["deck_slide_shapes"]["3"][0].update(caret_x=-999,ink_left=4000)
        verdict=verify_exact_text_transaction(before,after,[self.key],"$40.9M")
        self.assertEqual(verdict["status"],"PASS")
        self.assertEqual(verdict["collateral_diff"],[])

    def test_B_zoom_does_not_change_semantic_verdict(self):
        low=copy.deepcopy(self.before); high=copy.deepcopy(self.before)
        low["zoom"]=50; high["zoom"]=200
        self.assertEqual(normalize_deck(low),normalize_deck(high))

    def test_C_font_hinting_and_antialiasing_metadata_are_irrelevant(self):
        a=copy.deepcopy(self.before); b=copy.deepcopy(self.before)
        a.update(hinting="A",antialiasing="subpixel")
        b.update(hinting="B",antialiasing="grayscale")
        self.assertEqual(normalize_deck(a),normalize_deck(b))

    def test_D_ink_left_is_irrelevant(self):
        a=copy.deepcopy(self.before); b=copy.deepcopy(self.before)
        a["ink_left"]=1; b["ink_left"]=9999
        self.assertEqual(normalize_deck(a),normalize_deck(b))

    def test_E_ambiguous_semantic_target_aborts(self):
        duplicate=row(99,"Duplicate","$42.8M",x=900,y=430)
        ambiguous=state([self.target,duplicate,self.sibling])
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_TARGET_AMBIGUOUS"):
            resolve_target(ambiguous,slide=3,old="$42.8M")

    def test_F_sibling_collateral_mutation_fails_closed(self):
        after=copy.deepcopy(self.after)
        after["deck_slide_shapes"]["3"][1]["text"]="COLLATERAL"
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_SEMANTIC_DIFF_MISMATCH"):
            verify_exact_text_transaction(self.before,after,[self.key],"$40.9M")

    def test_G_save_without_persisted_state_is_not_semantically_complete(self):
        unchanged=copy.deepcopy(self.before)
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_SEMANTIC_DIFF_MISMATCH"):
            verify_exact_text_transaction(self.before,unchanged,[self.key],"$40.9M")

    def test_H_exact_single_change_passes(self):
        verdict=verify_exact_text_transaction(self.before,self.after,[self.key],"$40.9M")
        self.assertEqual(verdict["changed_semantic_targets"],1)
        self.assertEqual(verdict["observed_semantic_diff"],verdict["allowed_semantic_diff"])
        self.assertEqual(verdict["collateral_diff"],[])

    def test_I_missing_target_fails(self):
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_TARGET_MISSING"):
            resolve_target(self.before,slide=3,old="DOES NOT EXIST")

    def test_J_target_ambiguity_with_equal_structural_distance_fails(self):
        a=row(10,"A","214",x=100,y=100)
        b=row(11,"B","214",x=100,y=100)
        ambiguous=state([a,b])
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_TARGET_AMBIGUOUS"):
            resolve_target(ambiguous,slide=3,old="214",hint_x=500,hint_y=500)

    def test_K_official_evaluator_rejection_remains_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/"candidate-sha.txt").write_text("a"*40)
            (root/"task-id.txt").write_text("091")
            (root/"task-rc.txt").write_text("0")
            p=root/"results"/"pyautogui"/"x"/"tasks"/"091"
            p.mkdir(parents=True)
            (p/"result.txt").write_text("0.9")
            summary=root/"results"/"summary"; summary.mkdir(parents=True)
            (summary/"results.json").write_text(json.dumps([
                {"task_id":"091","status":"success","score":0.9}
            ]))
            with self.assertRaisesRegex((ValueError,AssertionError),"OFFICIAL_SCORE_NOT_EXACTLY_ONE"):
                exact_result(root,"a"*40)

    def test_L_unexpected_relationship_change_fails(self):
        rel=[{"type":"slideLayout","target":"ppt/slideLayouts/slideLayout1.xml","target_mode":""}]
        before=state([self.target,self.sibling],relationships=rel)
        after=copy.deepcopy(before)
        after["deck_slide_shapes"]["3"][0]["text"]="$40.9M"
        after["deck_file"]["sha256"]="b"*64
        after["deck_slide_relationships"]["3"].append(
            {"type":"hyperlink","target":"https://example.invalid","target_mode":"External"})
        key=next(key for key,value in normalize_deck(before).items()
                 if value["text"]=="$42.8M")
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_SEMANTIC_DIFF_MISMATCH"):
            verify_exact_text_transaction(before,after,[key],"$40.9M")

    def test_M_roundtrip_divergence_fails(self):
        reverted=copy.deepcopy(self.before)
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_ROUNDTRIP_VALUE_MISMATCH"):
            assert_roundtrip(reverted,[self.key],"$40.9M")

    def test_adversarial_corruption_rejected_then_clean_transaction_passes(self):
        corrupted=copy.deepcopy(self.after)
        corrupted["deck_slide_shapes"]["3"][1]["text"]="104%%"
        with self.assertRaisesRegex(SemanticTransactionError,"TASK091_SEMANTIC_DIFF_MISMATCH"):
            verify_exact_text_transaction(self.before,corrupted,[self.key],"$40.9M")
        clean=verify_exact_text_transaction(self.before,self.after,[self.key],"$40.9M")
        self.assertEqual(clean["status"],"PASS")

    def test_semantic_diff_equality_not_subset(self):
        before=normalize_deck(self.before); after=normalize_deck(self.after)
        observed=semantic_diff(before,after)
        self.assertEqual(len(observed),1)
        self.assertEqual(observed[0]["field"],"text")

    def test_certifier_rejects_legacy_caret_decision_path(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            events=[{"status":value} for value in SEMANTIC_REQUIRED_STATUSES]
            events += [
                {"status":"TASK091_SEMANTIC_TEXT_TRANSACTIONS_COMPLETE"},
                {"status":"TASK091_SECTION_E_FORMAT_VERIFIED"},
                {"status":"TASK091_SPECIALIST_ACTION_ISSUED",
                 "phase":"semantic-save","pending_edit":None},
            ]
            (root/"shim.jsonl").write_text(
                "".join(json.dumps(e)+"\n" for e in events),encoding="utf-8")
            self.assertEqual(verify_semantic_architecture(root)["status"],
                             "TASK091_SEMANTIC_ARCHITECTURE_PASS")
            events.append({"status":"TASK091_SPECIALIST_ACTION_ISSUED",
                           "phase":"move-table-caret-to-proven-start",
                           "pending_edit":None})
            (root/"shim.jsonl").write_text(
                "".join(json.dumps(e)+"\n" for e in events),encoding="utf-8")
            with self.assertRaisesRegex((ValueError,AssertionError),"TASK091_LEGACY_PHASE_EXECUTED"):
                verify_semantic_architecture(root)


if __name__=="__main__":
    unittest.main()
