import copy
import json
import tempfile
import unittest
from pathlib import Path

from arbm091.semantic_runtime import next_text_action
from arbm091.score_tracker import SEMANTIC_REQUIRED_STATUSES, verify_semantic_architecture


def base_state():
    return {
        "schema":1,
        "stable":True,
        "screen":[0,0,1920,1080],
        "window":{"bbox":[70,27,1850,1053],"title":"Operating_Committee_Rebaseline_Draft.pptx - WPS Presentation"},
        "active_slide":3,
        "deck_file":{"sha256":"a"*64,"slide_size":{"w":12192000,"h":6858000}},
        "deck_slide_shapes":{
            "3":[{
                "id":-13001003,"name":"Table 12#r1c2","text":"$42.8M",
                "kind":"table-cell","frame_id":13,"row":1,"col":2,
                "geometry":{"x":3877056,"y":2088750,"w":1563624,"h":607422},
                "font_sizes":[1600],"fill_rgb":"",
            }],
        },
    }


class SemanticRuntimeTests(unittest.TestCase):
    def test_transaction_has_no_caret_or_character_navigation(self):
        ws=base_state()
        state={"slide":3}
        plan=((3,843,404,"$42.8M","$40.9M"),)
        select=next_text_action(state,ws,plan)
        self.assertEqual(select["specialist_phase"],"semantic-target-select")
        self.assertIn("doubleClick",select["command"])
        self.assertNotIn("caret",select["command"].casefold())
        self.assertNotIn("caret",select["specialist_phase"].casefold())
        preflight=next_text_action(state,ws,plan)
        self.assertEqual(preflight["specialist_phase"],"semantic-cover-autofit-pane-open")
        self.assertIn("hotkey('shift', 'f10')",preflight["command"])
        self.assertIn("press('o')",preflight["command"])
        ws_pane=copy.deepcopy(ws)
        ws_pane["screenshot_sha256"]="c"*64
        diag=next_text_action(state,ws_pane,plan)
        self.assertEqual(diag["action"],"terminal")
        self.assertEqual(diag["reason"],"TASK091_COVERTITLE_AUTOFIT_PANE_CAPTURED")
        self.assertIn("ctrl', 'a",mutation["command"])
        self.assertIn("$40.9M",mutation["command"])
        forbidden=("press('left'","press('right'","press('home')","ink_left","caret_x")
        for token in forbidden:
            self.assertNotIn(token,mutation["command"])

    def test_contained_target_precondition_uses_resolved_shape_baseline(self):
        ws=base_state()
        ws["active_slide"]=1
        ws["deck_slide_shapes"]={"1":[{
            "id":6,"name":"CoverTitle",
            "text":"H2 Operating Committee Pack\nGrowth Plan Draft",
            "kind":"shape","frame_id":0,"row":-1,"col":-1,
            "geometry":{"x":749808,"y":1078992,"w":5852160,"h":1234440},
            "font_sizes":[2400],"fill_rgb":"",
        }]}
        ws["deck_slide_relationships"]={"1":[]}
        state={"slide":1}
        plan=((1,745,335,"Growth Plan Draft",
               "H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline"),)
        select=next_text_action(state,ws,plan)
        self.assertEqual(select["specialist_phase"],"semantic-target-select")
        self.assertEqual(
            state["semantic_tx"]["before_target_text"],
            "H2 Operating Committee Pack\nGrowth Plan Draft",
        )
        mutation=next_text_action(state,ws,plan)
        self.assertEqual(mutation["specialist_phase"],"semantic-text-mutation")
        self.assertNotEqual(mutation.get("action"),"terminal")
        self.assertIn("hotkey('ctrl', 'h')",mutation["command"])
        self.assertIn("Growth Plan Draft",mutation["command"])
        self.assertIn("Stabilize-and-Recover Rebaseline",mutation["command"])
        self.assertIn("hotkey('alt', 'a')",mutation["command"])
        self.assertNotIn("hotkey('ctrl', 'a')",mutation["command"])
        self.assertNotIn("press('home')",mutation["command"])
        self.assertNotIn("press('left'",mutation["command"])

    def test_contained_replace_rejects_boundary_drift(self):
        from arbm091.semantic_runtime import _contained_replacement
        with self.assertRaisesRegex(Exception,"TASK091_CONTAINED_REPLACE_BOUNDARY_DRIFT"):
            _contained_replacement(
                "H2 Operating Committee Pack\nGrowth Plan Draft",
                "Growth Plan Draft",
                "CORRUPTED PREFIX\nStabilize-and-Recover Rebaseline",
            )

    def test_exact_persisted_diff_advances_only_after_roundtrip(self):
        ws=base_state()
        state={"slide":3}
        plan=((3,843,404,"$42.8M","$40.9M"),)
        next_text_action(state,ws,plan)  # select
        next_text_action(state,ws,plan)  # write
        commit=next_text_action(state,ws,plan)
        self.assertEqual(commit["specialist_phase"],"semantic-edit-finalize")
        save=next_text_action(state,ws,plan)
        self.assertEqual(save["specialist_phase"],"semantic-save")
        after=copy.deepcopy(ws)
        after["deck_file"]["sha256"]="b"*64
        after["deck_slide_shapes"]["3"][0]["text"]="$40.9M"
        reread=next_text_action(state,after,plan)
        self.assertEqual(reread["specialist_phase"],"semantic-roundtrip-reread")
        passed=next_text_action(state,after,plan)
        self.assertEqual(passed["checkpoint"],"TASK091_SEMANTIC_TRANSACTION_PASS")
        self.assertEqual(state["semantic_index"],1)
        self.assertTrue(state["semantic_evidence"][0]["diff_budget_exact"])
        self.assertTrue(state["semantic_evidence"][0]["no_collateral_mutation"])

    def test_collateral_style_change_is_terminal(self):
        ws=base_state()
        state={"slide":3}
        plan=((3,843,404,"$42.8M","$40.9M"),)
        next_text_action(state,ws,plan)
        next_text_action(state,ws,plan)
        next_text_action(state,ws,plan)
        next_text_action(state,ws,plan)
        bad=copy.deepcopy(ws)
        bad["deck_file"]["sha256"]="b"*64
        bad["deck_slide_shapes"]["3"][0]["text"]="$40.9M"
        bad["deck_slide_shapes"]["3"][0]["fill_rgb"]="FF0000"
        result=next_text_action(state,bad,plan)
        self.assertEqual(result["action"],"terminal")
        self.assertIn("TASK091_SEMANTIC_DIFF_MISMATCH",result["reason"])

    def test_unpersisted_save_is_terminal(self):
        ws=base_state()
        state={"slide":3}
        plan=((3,843,404,"$42.8M","$40.9M"),)
        next_text_action(state,ws,plan)
        next_text_action(state,ws,plan)
        next_text_action(state,ws,plan)
        next_text_action(state,ws,plan)
        result=next_text_action(state,ws,plan)
        self.assertEqual(result["action"],"terminal")

    def test_migration_route_precedes_and_seals_legacy_caret_path(self):
        shim=Path("scripts/osworld_free_mesh_shim.py").read_text(encoding="utf-8")
        runtime=Path("scripts/arbm091/semantic_runtime.py").read_text(encoding="utf-8")
        specialist=shim.split("def next_091_specialist_action",1)[1]
        deck_active=specialist.split("state['mode']='DECK_ACTIVE'",1)[1]
        gate="if not state.get('semantic_text_done')"
        boundary="# New Task 091 architecture boundary."
        legacy="# Historical replay compatibility only."
        self.assertIn(gate,deck_active)
        self.assertIn(boundary,deck_active)
        self.assertIn(legacy,deck_active)
        self.assertLess(deck_active.index(gate),deck_active.index(boundary))
        self.assertLess(deck_active.index(boundary),deck_active.index(legacy))
        sealed=deck_active[deck_active.index(boundary):deck_active.index(legacy)]
        self.assertIn("TASK091_LEGACY_TEXT_STATE_FORBIDDEN",sealed)
        self.assertIn("TASK091_SEMANTIC_PLAN_INCOMPLETE",sealed)
        self.assertIn("return None",sealed)
        self.assertIn('state["spatial_index"]=len(plan)',runtime)
        for forbidden in (
            "_task091_caret","CARET_NOT_AT_START","CARET_GEOMETRY_UNPROVEN",
            "ink_left","caret_x","press('home')","press('left'",
        ):
            self.assertNotIn(forbidden,runtime)

    def test_semantic_certifier_rejects_any_legacy_phase(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            events=[{"status":value} for value in SEMANTIC_REQUIRED_STATUSES]
            events.extend([
                {"status":"TASK091_SEMANTIC_TEXT_TRANSACTIONS_COMPLETE"},
                {"status":"TASK091_SECTION_E_FORMAT_VERIFIED"},
                {"status":"TASK091_SPECIALIST_ACTION_ISSUED",
                 "phase":"semantic-save","pending_edit":None},
            ])
            (root/"shim.jsonl").write_text(
                "".join(json.dumps(row)+"\n" for row in events),encoding="utf-8")
            self.assertEqual(
                verify_semantic_architecture(root)["status"],
                "TASK091_SEMANTIC_ARCHITECTURE_PASS")
            events.append({
                "status":"TASK091_SPECIALIST_ACTION_ISSUED",
                "phase":"move-table-caret-to-proven-start","pending_edit":None,
            })
            (root/"shim.jsonl").write_text(
                "".join(json.dumps(row)+"\n" for row in events),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"TASK091_LEGACY_PHASE_EXECUTED"):
                verify_semantic_architecture(root)

    def test_section_e_decision_path_has_no_caret_dependency(self):
        from pathlib import Path
        shim=Path("scripts/osworld_free_mesh_shim.py").read_text(encoding="utf-8")
        body=shim.split("def _task091_section_e_format_step",1)[1].split(
            "def _task091_system_check_close",1)[0]
        self.assertIn("task091_verify_font_transaction",body)
        self.assertIn("section-e-semantic-roundtrip",body)
        self.assertNotIn("_task091_caret",body)
        self.assertNotIn("CARET_UNPROVEN",body)

    def test_transient_during_semantic_transaction_is_fail_closed(self):
        from pathlib import Path
        shim=Path("scripts/osworld_free_mesh_shim.py").read_text(encoding="utf-8")
        specialist=shim.split("def next_091_specialist_action",1)[1]
        transient=specialist.split("if app == 'wps-transient':",1)[1].split(
            "if app != 'wps-presentation':",1)[0]
        self.assertIn("TASK091_SEMANTIC_TRANSACTION_INTERRUPTED_BY_TRANSIENT",transient)
        self.assertIn("TASK091_SECTION_E_SEMANTIC_INTERRUPTED_BY_TRANSIENT",transient)


if __name__=="__main__":
    unittest.main()
