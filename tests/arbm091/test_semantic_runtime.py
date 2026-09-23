import copy
import unittest

from arbm091.semantic_runtime import next_text_action


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
        mutation=next_text_action(state,ws,plan)
        self.assertEqual(mutation["specialist_phase"],"semantic-text-mutation")
        self.assertIn("ctrl', 'a",mutation["command"])
        self.assertIn("$40.9M",mutation["command"])
        forbidden=("press('left'","press('right'","press('home')","ink_left","caret_x")
        for token in forbidden:
            self.assertNotIn(token,mutation["command"])

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
        from pathlib import Path
        shim=Path("scripts/osworld_free_mesh_shim.py").read_text(encoding="utf-8")
        runtime=Path("scripts/arbm091/semantic_runtime.py").read_text(encoding="utf-8")
        specialist=shim.split("def next_091_specialist_action",1)[1]
        gate="if not state.get('semantic_text_done')"
        legacy="pending=state.get('pending_edit')"
        self.assertIn(gate,specialist)
        self.assertIn(legacy,specialist)
        self.assertLess(specialist.index(gate),specialist.index(legacy))
        self.assertIn('state["spatial_index"]=len(plan)',runtime)
        for forbidden in (
            "_task091_caret","CARET_NOT_AT_START","CARET_GEOMETRY_UNPROVEN",
            "ink_left","caret_x","press('home')","press('left'",
        ):
            self.assertNotIn(forbidden,runtime)

    def test_section_e_decision_path_has_no_caret_dependency(self):
        from pathlib import Path
        shim=Path("scripts/osworld_free_mesh_shim.py").read_text(encoding="utf-8")
        body=shim.split("def _task091_section_e_format_step",1)[1].split(
            "def _task091_system_check_close",1)[0]
        self.assertIn("task091_verify_font_transaction",body)
        self.assertIn("section-e-semantic-roundtrip",body)
        self.assertNotIn("_task091_caret",body)
        self.assertNotIn("CARET_UNPROVEN",body)


if __name__=="__main__":
    unittest.main()
