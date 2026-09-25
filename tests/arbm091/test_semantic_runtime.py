import copy
import json
import tempfile
import unittest
from pathlib import Path

from arbm091.semantic_runtime import _current_autofit_group, next_text_action, _snapshot
from arbm091.semantic_transaction import model_sha256, normalize_deck
from arbm091.score_tracker import SEMANTIC_REQUIRED_STATUSES, verify_semantic_architecture


def base_state():
    return {
        "schema":1,
        "stable":True,
        "screen":[0,0,1920,1080],
        "window":{"bbox":[70,27,1850,1053],"title":"Operating_Committee_Rebaseline_Draft.pptx - WPS Presentation"},
        "active_slide":3,
        "deck_file":{"sha256":"a"*64,"slide_size":{"w":12192000,"h":6858000}},
        "slide_canvas_bbox":[443,194,1413,795],
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
    def _cover_recovery_fixture(self):
        ws=base_state()
        ws["active_slide"]=1
        ws["screenshot_sha256"]="a"*64
        ws["deck_file"]["slide_size"]={"w":12191365,"h":6858000}
        ws["slide_canvas_bbox"]=[352,263,1135,638]
        ws["deck_slide_shapes"]={"1":[
            {"id":13,"name":"CoverStatValue_0","kind":"shape","text":"$42.8M",
             "geometry":{"x":8339327,"y":2167128,"w":2560320,"h":219456},
             "autofit_mode":"RESIZE_SHAPE_TO_FIT_TEXT","font_sizes":[2100],"fill_rgb":""},
            {"id":16,"name":"CoverStatValue_1","kind":"shape","text":"$2.6M",
             "geometry":{"x":1,"y":2,"w":3,"h":4}}]}
        before=_snapshot(ws)
        tx={"stage":"save-issued","index":0,"slide":1,"old":"$42.8M","new":"$40.9M",
            "target_key":[1,"shape",13,"CoverStatValue_0"],
            "before_state":before,"before_model_sha256":model_sha256(normalize_deck(before)),
            "before_deck_sha256":"a"*64,"autofit_selection_confirmed":True,
            "contract":{"status":"PASS","target_resolved":True,"target_unique":True,
                        "precondition":True,"mutation_authorized":True}}
        wrong=copy.deepcopy(ws)
        wrong["deck_file"]["sha256"]="b"*64
        wrong["deck_slide_shapes"]["1"][0]["text"]="$40.9MM"
        wrong["deck_slide_shapes"]["1"][0]["autofit_mode"]="DO_NOT_AUTOFIT"
        return ws,wrong,{"slide":1,"semantic_tx":tx},((1,1338,393,"$42.8M","$40.9M"),)

    def test_cover_wrong_text_recovers_once_and_requires_roundtrip(self):
        _,wrong,state,plan=self._cover_recovery_fixture()
        select=next_text_action(state,wrong,plan)
        self.assertEqual(select["specialist_phase"],"semantic-cover-recovery-select")
        selected=copy.deepcopy(wrong)
        selected["screenshot_sha256"]="b"*64
        write=next_text_action(state,selected,plan)
        self.assertEqual(write["specialist_phase"],"semantic-cover-recovery-write")
        self.assertIn("pyautogui.hotkey('alt', 'n')",write["command"])
        self.assertIn("pyautogui.hotkey('alt', 'r')",write["command"])
        self.assertNotIn("pyautogui.press('delete')",write["command"])
        self.assertEqual(next_text_action(state,selected,plan)["specialist_phase"],
                         "semantic-cover-recovery-commit")
        self.assertEqual(next_text_action(state,selected,plan)["specialist_phase"],
                         "semantic-cover-recovery-save")
        fixed=copy.deepcopy(selected)
        fixed["deck_file"]["sha256"]="c"*64
        fixed["deck_slide_shapes"]["1"][0]["text"]="$40.9M"
        self.assertEqual(next_text_action(state,fixed,plan)["specialist_phase"],
                         "semantic-cover-recovery-roundtrip")
        done=next_text_action(state,fixed,plan)
        self.assertEqual(done["checkpoint"],"TASK091_SEMANTIC_TRANSACTION_PASS")
        self.assertEqual(state["semantic_index"],1)

    def test_cover_recovery_vetoes_collateral_geometry_and_second_attempt(self):
        _,wrong,state,plan=self._cover_recovery_fixture()
        collateral=copy.deepcopy(wrong)
        collateral["deck_slide_shapes"]["1"][1]["text"]="changed"
        self.assertEqual(next_text_action(copy.deepcopy(state),collateral,plan)["action"],"terminal")
        geometry=copy.deepcopy(wrong)
        geometry["deck_slide_shapes"]["1"][0]["geometry"]["h"]=219457
        self.assertEqual(next_text_action(copy.deepcopy(state),geometry,plan)["action"],"terminal")
        state["semantic_tx"]["recovery_attempts"]=1
        self.assertEqual(next_text_action(state,wrong,plan)["action"],"terminal")

    def test_artifact_calibrated_canvas_maps_cover_stat(self):
        ws=base_state()
        ws["active_slide"]=1
        ws["deck_file"]["slide_size"]={"w":12191365,"h":6858000}
        ws["slide_canvas_bbox"]=[352,263,1135,638]
        ws["deck_slide_shapes"]={"1":[{
            "id":13,"name":"CoverStatValue_0","text":"$42.8M","kind":"shape",
            "geometry":{"x":8339327,"y":2167128,"w":2560320,"h":219456},
            "font_sizes":[2100,2100],"fill_rgb":"",
        }]}
        state={"slide":1}
        action=next_text_action(state,ws,((1,1338,393,"$42.8M","$40.9M"),))
        self.assertEqual(action["specialist_phase"],"semantic-target-select")
        self.assertEqual((action["target"]["cx"],action["target"]["cy"]),(1248,475))
        self.assertIn("doubleClick(1248, 475",action["command"])

    def test_cover_stat_freezes_autofit_then_reselects_and_direct_writes(self):
        ws=base_state()
        ws["active_slide"]=1
        ws["source"]="cover-stat-before"
        ws["screenshot_sha256"]="a"*64
        ws["deck_file"]["slide_size"]={"w":12191365,"h":6858000}
        ws["slide_canvas_bbox"]=[352,263,1135,638]
        ws["deck_slide_shapes"]={"1":[{
            "id":13,"name":"CoverStatValue_0","text":"$42.8M","kind":"shape",
            "geometry":{"x":8339327,"y":2167128,"w":2560320,"h":219456},
            "font_sizes":[2100,2100],"fill_rgb":"",
            "autofit_mode":"RESIZE_SHAPE_TO_FIT_TEXT",
        }]}
        ws["deck_slide_relationships"]={"1":[]}
        state={"slide":1}
        plan=((1,1338,393,"$42.8M","$40.9M"),)

        select=next_text_action(state,ws,plan)
        self.assertEqual(select["specialist_phase"],"semantic-target-select")
        self.assertEqual((select["target"]["cx"],select["target"]["cy"]),(1248,475))

        options=copy.deepcopy(ws)
        options["source"]="cover-stat-options"
        options["screenshot_sha256"]="b"*64
        options["controls"]=self._current_group()
        freeze=next_text_action(state,options,plan)
        self.assertEqual(freeze["specialist_phase"],"semantic-cover-autofit-do-not-select")
        self.assertEqual((freeze["target"]["cx"],freeze["target"]["cy"]),(1560,674))

        frozen=copy.deepcopy(options)
        frozen["source"]="cover-stat-frozen"
        frozen["screenshot_sha256"]="c"*64
        for control in frozen["controls"]:
            control["selected"]=control["label"]=="Do not Autofit"
        reselect=next_text_action(state,frozen,plan)
        self.assertEqual(reselect["specialist_phase"],"semantic-autofit-reselect")
        self.assertIn("doubleClick(1248, 475",reselect["command"])
        self.assertEqual(
            tuple(state["semantic_tx"]["before_state"]["deck_slide_shapes"]["1"][0]["geometry"][k]
                  for k in ("x","y","w","h")),
            (8339327,2167128,2560320,219456),
        )

        mutation=next_text_action(state,frozen,plan)
        self.assertEqual(mutation["specialist_phase"],"semantic-text-mutation")
        command=mutation["command"]
        self.assertIn("pyautogui.hotkey('ctrl', 'h')",command)
        self.assertIn("pyautogui.write('$42.8M', interval=0.08)",command)
        self.assertIn("pyautogui.write('$40.9M', interval=0.08)",command)
        self.assertLess(command.index("hotkey('alt', 'n')"),command.index("hotkey('alt', 'r')"))
        self.assertNotIn("pyautogui.hotkey('ctrl', 'a')",command)
        self.assertNotIn("pyautogui.press('delete')",command)
        self.assertNotIn("f2",command.casefold())
        self.assertEqual(state["semantic_tx"]["mutation_mode"],"autofit-locked-single-native-replace")

    def test_second_cover_stat_uses_locked_autofit_single_replace(self):
        ws=base_state()
        ws["active_slide"]=1
        ws["source"]="cover-stat-1-before"
        ws["screenshot_sha256"]="a"*64
        ws["deck_file"]["slide_size"]={"w":12191365,"h":6858000}
        ws["slide_canvas_bbox"]=[352,263,1135,638]
        ws["controls"]=[]
        ws["deck_slide_shapes"]={"1":[{
            "id":16,"name":"CoverStatValue_1","text":"$2.6M","kind":"shape",
            "geometry":{"x":8339327,"y":3355848,"w":2560320,"h":219456},
            "font_sizes":[2100,2100],"fill_rgb":"",
            "autofit_mode":"RESIZE_SHAPE_TO_FIT_TEXT",
        }]}
        ws["deck_slide_relationships"]={"1":[]}
        state={"slide":1}
        plan=((1,1338,500,"$2.6M","$2.8M"),)

        select=next_text_action(state,ws,plan)
        self.assertEqual(select["specialist_phase"],"semantic-target-select")
        self.assertEqual(state["semantic_tx"]["target_key"],[1,"shape",16,"CoverStatValue_1"])

        mutation=next_text_action(state,ws,plan)
        command=mutation["command"]
        self.assertEqual(mutation["specialist_phase"],"semantic-coverstat1-direct-replace")
        self.assertIn("pyautogui.hotkey('ctrl', 'h')",command)
        self.assertIn("pyautogui.write('$2.6M', interval=0.08)",command)
        self.assertIn("pyautogui.write('$2.8M', interval=0.08)",command)
        self.assertNotIn("pyautogui.hotkey('ctrl', 'a')",command)
        self.assertNotIn("f2",command.casefold())
        self.assertNotIn("TEXT OPTIONS",command)
        self.assertNotIn("PANEL DISCLOSURE",command)
        self.assertEqual(state["semantic_tx"]["mutation_mode"],
                         "geometry-locked-single-native-replace")

    def test_second_cover_stat_bypasses_panel_controls_and_stays_fail_closed(self):
        ws=base_state()
        ws["active_slide"]=1
        ws["source"]="cover-stat-1-before"
        ws["screenshot_sha256"]="a"*64
        ws["deck_file"]["slide_size"]={"w":12191365,"h":6858000}
        ws["slide_canvas_bbox"]=[352,263,1135,638]
        ws["controls"]=[]
        ws["deck_slide_shapes"]={"1":[{
            "id":16,"name":"CoverStatValue_1","text":"$2.6M","kind":"shape",
            "geometry":{"x":8339327,"y":3355848,"w":2560320,"h":219456},
            "font_sizes":[2100,2100],"fill_rgb":"",
            "autofit_mode":"RESIZE_SHAPE_TO_FIT_TEXT",
        }]}
        ws["deck_slide_relationships"]={"1":[]}
        state={"slide":1}
        plan=((1,1338,500,"$2.6M","$2.8M"),)

        self.assertEqual(next_text_action(state,ws,plan)["specialist_phase"],"semantic-target-select")
        action=next_text_action(state,ws,plan)
        self.assertEqual(action["specialist_phase"],"semantic-coverstat1-direct-replace")
        self.assertIn("pyautogui.hotkey('ctrl', 'h')",action["command"])
        self.assertIn("pyautogui.write('$2.6M', interval=0.08)",action["command"])
        self.assertIn("pyautogui.write('$2.8M', interval=0.08)",action["command"])
        self.assertNotIn("TEXT OPTIONS",action["command"])
        self.assertNotIn("PANEL DISCLOSURE",action["command"])
        self.assertEqual(state["semantic_tx"]["mutation_mode"],
                         "geometry-locked-single-native-replace")

    def test_cover_title_reuses_current_text_options_without_reopening_panel(self):
        ws=base_state()
        ws["active_slide"]=1
        ws["deck_slide_shapes"]={"1":[{
            "id":6,"name":"CoverTitle",
            "text":"H2 Operating Committee Pack\nGrowth Plan Draft",
            "kind":"shape","frame_id":0,"row":-1,"col":-1,
            "geometry":{"x":749808,"y":1078992,"w":5852160,"h":1234440},
            "font_sizes":[2400],"fill_rgb":"",
            "autofit_mode":"RESIZE_SHAPE_TO_FIT_TEXT",
        }]}
        ws["deck_slide_relationships"]={"1":[]}
        state={"slide":1}
        plan=((1,745,335,"Growth Plan Draft",
               "H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline"),)

        select=next_text_action(state,ws,plan)
        self.assertEqual(select["specialist_phase"],"semantic-target-select")

        current=copy.deepcopy(ws)
        current["source"]="0003-01-after"
        current["screenshot_sha256"]="c"*64
        current["controls"]=[{
            "label":"TEXT OPTIONS","role":"visual-tab","pid":2820,
            "application":"wpsoffice wpsoffice","bbox":[1640,190,150,28],
            "showing":True,"enabled":True,
        }]
        action=next_text_action(state,current,plan)
        self.assertEqual(action["specialist_phase"],"semantic-cover-autofit-text-options-open")
        self.assertEqual(action["command"],"pyautogui.click(1715, 204)")
        self.assertEqual(action["target"]["label"],"TEXT OPTIONS")
        self.assertNotIn("shift",action["command"].casefold())
        self.assertNotIn("f10",action["command"].casefold())
        self.assertEqual(state["semantic_tx"]["autofit_preflight_source"],"current-frame-text-options")
        self.assertEqual(state["semantic_tx"]["autofit_panel_points"]["text_options"],[1715,204])

    def test_missing_canvas_is_rejected_fail_closed(self):
        ws=base_state(); ws.pop("slide_canvas_bbox")
        result=next_text_action({"slide":3},ws,((3,843,404,"$42.8M","$40.9M"),))
        self.assertEqual(result,{"action":"terminal","reason":"TASK091_SLIDE_CANVAS_UNPROVEN"})

    def test_wrong_canvas_aspect_is_rejected_fail_closed(self):
        ws=base_state(); ws["slide_canvas_bbox"]=[352,263,1135,500]
        result=next_text_action({"slide":3},ws,((3,843,404,"$42.8M","$40.9M"),))
        self.assertEqual(result,{"action":"terminal","reason":"TASK091_SLIDE_CANVAS_ASPECT_MISMATCH"})

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
        self.assertIn("press('f2')",mutation["command"])
        self.assertLess(mutation["command"].index("press('f2')"),mutation["command"].index("ctrl', 'a"))
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
        preflight=next_text_action(state,ws,plan)
        self.assertEqual(preflight["specialist_phase"],"semantic-cover-autofit-pane-open")
        self.assertIn("hotkey('shift', 'f10')",preflight["command"])
        self.assertIn("press('o')",preflight["command"])
        ws_pane=copy.deepcopy(ws)
        ws_pane["source"]="0007-03-after"
        ws_pane["screenshot_sha256"]="c"*64
        ws_pane["controls"]=[{"label":"TEXT OPTIONS","role":"page tab","pid":2883,
            "application":"WPS Office","bbox":[1660,200,140,38],"showing":True,"enabled":True}]
        diag=next_text_action(state,ws_pane,plan)
        self.assertEqual(diag["specialist_phase"],"semantic-cover-autofit-text-options-open")
        self.assertEqual(diag["target"]["source"],"task091-panel-canonical")
        self.assertEqual(diag["target"]["label"],"TEXT OPTIONS")
        self.assertEqual(state["semantic_tx"]["autofit_panel_points"]["text_options"],[1730,219])
        ws_options=copy.deepcopy(ws)
        ws_options["source"]="0008-01-after"
        ws_options["screenshot_sha256"]="d"*64
        ws_options["controls"]=[{"label":"Text Box","role":"page tab","pid":2883,
            "application":"WPS Office","bbox":[1660,232,140,38],"showing":True,"enabled":True}]
        textbox=next_text_action(state,ws_options,plan)
        self.assertEqual(textbox["specialist_phase"],"semantic-cover-autofit-textbox-pane-open")
        self.assertEqual(textbox["target"]["source"],"task091-panel-canonical")
        self.assertEqual(textbox["target"]["label"],"Text Box")
        ws_textbox=copy.deepcopy(ws)
        ws_textbox["source"]="0009-01-after"
        ws_textbox["screenshot_sha256"]="e"*64
        ws_textbox["controls"]=[{"label":"PANEL DISCLOSURE","role":"visual-disclosure","pid":2883,
            "application":"WPS Office","bbox":[1532,341,5,10],"showing":True,"enabled":True}]
        disclosure=next_text_action(state,ws_textbox,plan)
        self.assertEqual(disclosure["action"],"exec")
        self.assertEqual(disclosure["specialist_phase"],"semantic-cover-autofit-disclosure-open")
        self.assertEqual(disclosure["target"]["label"],"PANEL DISCLOSURE")
        ws_options_open=copy.deepcopy(ws)
        ws_options_open["source"]="0010-01-after"
        ws_options_open["screenshot_sha256"]="f"*64
        ws_options_open["controls"]=[
            {"label":"Do not Autofit","role":"visual-radio","pid":2883,"application":"WPS Office",
             "bbox":[1551,665,17,17],"showing":True,"enabled":True,"selected":False},
            {"label":"Shrink text on overflow","role":"visual-radio","pid":2883,"application":"WPS Office",
             "bbox":[1551,695,17,17],"showing":True,"enabled":True,"selected":False},
            {"label":"Resize shape to fit text","role":"visual-radio","pid":2883,"application":"WPS Office",
             "bbox":[1551,725,17,17],"showing":True,"enabled":True,"selected":True},
        ]
        ws_options_open["deck_slide_shapes"]["1"][0]["autofit_mode"]="RESIZE_SHAPE_TO_FIT_TEXT"
        select_autofit=next_text_action(state,ws_options_open,plan)
        self.assertEqual(select_autofit["specialist_phase"],"semantic-cover-autofit-do-not-select")
        self.assertEqual(select_autofit["target"]["label"],"Do not Autofit")
        ws_selected=copy.deepcopy(ws_options_open)
        ws_selected["screenshot_sha256"]="1"*64
        for control in ws_selected["controls"]:
            control["selected"]=control["label"]=="Do not Autofit"
        confirmed=next_text_action(state,ws_selected,plan)
        self.assertEqual(confirmed["checkpoint"],"TASK091_COVERTITLE_AUTOFIT_SELECTION_CONFIRMED")
        self.assertTrue(state["semantic_tx"]["autofit_preflight_done"])
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

    def _coversub_state_with_current_autofit_group(self):
        ws=base_state()
        ws["active_slide"]=1
        ws["source"]="0015-01-after"
        ws["screenshot_sha256"]="a"*64
        ws["deck_slide_shapes"]={"1":[{
            "id":7,"name":"CoverSub",
            "text":"Northstar Cloud\nPrepared for July Operating Committee review\nPlanning posture: accelerate growth through H2 scale-up",
            "kind":"shape","frame_id":0,"row":-1,"col":-1,
            "geometry":{"x":768096,"y":2743200,"w":5669280,"h":1280160},
            "font_sizes":[1800,1800,1300,1300,1300,1300],"fill_rgb":"",
            "autofit_mode":"RESIZE_SHAPE_TO_FIT_TEXT",
        }]}
        ws["deck_slide_relationships"]={"1":[]}
        return ws

    def _current_group(self):
        return [
            {"label":"Do not Autofit","role":"visual-radio","pid":2701,"owner_id":50331653,
             "application":"wpsoffice wpsoffice","bbox":[1553,667,14,14],
             "frame_bbox":[70,27,1850,1053],"frame_visual_sha256":"9"*64,
             "structural_family":"wps-autofit-radio-group-v2","structural_index":0,
             "showing":True,"enabled":True,"selected":False},
            {"label":"Shrink text on overflow","role":"visual-radio","pid":2701,"owner_id":50331653,
             "application":"wpsoffice wpsoffice","bbox":[1553,697,14,14],
             "frame_bbox":[70,27,1850,1053],"frame_visual_sha256":"9"*64,
             "structural_family":"wps-autofit-radio-group-v2","structural_index":1,
             "showing":True,"enabled":True,"selected":False},
            {"label":"Resize shape to fit text","role":"visual-radio","pid":2701,"owner_id":50331653,
             "application":"wpsoffice wpsoffice","bbox":[1553,727,14,14],
             "frame_bbox":[70,27,1850,1053],"frame_visual_sha256":"9"*64,
             "structural_family":"wps-autofit-radio-group-v2","structural_index":2,
             "showing":True,"enabled":True,"selected":True},
        ]

    def test_coversub_reuses_published_current_frame_autofit_group(self):
        ws=self._coversub_state_with_current_autofit_group()
        state={"slide":1}
        plan=((1,900,520,
               "Planning posture: accelerate growth through H2 scale-up",
               "Northstar Cloud\nPrepared for July Operating Committee review\nPlanning posture: stabilize and recover with disciplined sequencing"),)
        select=next_text_action(state,ws,plan)
        self.assertEqual(select["specialist_phase"],"semantic-target-select")
        observed=copy.deepcopy(ws)
        observed["source"]="0016-01-after"
        observed["screenshot_sha256"]="b"*64
        observed["controls"]=self._current_group()
        direct=next_text_action(state,observed,plan)
        self.assertEqual(direct["specialist_phase"],"semantic-cover-autofit-do-not-select")
        self.assertEqual(direct["target"]["label"],"Do not Autofit")
        self.assertEqual(direct["target"]["control_pid"],2701)
        self.assertEqual((direct["target"]["x"],direct["target"]["y"],direct["target"]["w"],direct["target"]["h"]),
                         (1553,667,14,14))
        self.assertNotIn("shift', 'f10",direct["command"])
        self.assertEqual(state["semantic_tx"]["autofit_preflight_source"],
                         "current-frame-published-group")
        self.assertEqual(
            tuple(state["semantic_tx"]["before_state"]["deck_slide_shapes"]["1"][0]["geometry"][k]
                  for k in ("x","y","w","h")),
            (768096,2743200,5669280,1280160),
        )

    def test_current_autofit_group_absent_rejected(self):
        ws=self._coversub_state_with_current_autofit_group()
        tx={"selection_before_screenshot_sha256":"a"*64}
        with self.assertRaisesRegex(Exception,"CURRENT_GROUP_ABSENT"):
            _current_autofit_group(ws,tx)

    def test_current_autofit_group_ambiguous_rejected(self):
        ws=self._coversub_state_with_current_autofit_group()
        ws["source"]="0016-01-after"; ws["screenshot_sha256"]="b"*64
        ws["controls"]=self._current_group()+[copy.deepcopy(self._current_group()[0])]
        tx={"selection_before_screenshot_sha256":"a"*64}
        with self.assertRaisesRegex(Exception,"RADIO_GROUP_NOT_OBSERVED"):
            _current_autofit_group(ws,tx)

    def test_current_autofit_group_wrong_owner_rejected(self):
        ws=self._coversub_state_with_current_autofit_group()
        ws["source"]="0016-01-after"; ws["screenshot_sha256"]="b"*64
        ws["controls"]=self._current_group()
        ws["controls"][1]["owner_id"]=999
        tx={"selection_before_screenshot_sha256":"a"*64}
        with self.assertRaisesRegex(Exception,"WRONG_OWNER"):
            _current_autofit_group(ws,tx)

    def test_current_autofit_group_stale_frame_rejected(self):
        ws=self._coversub_state_with_current_autofit_group()
        ws["source"]="0016-01-after"; ws["screenshot_sha256"]="a"*64
        ws["controls"]=self._current_group()
        tx={"selection_before_screenshot_sha256":"a"*64}
        with self.assertRaisesRegex(Exception,"STALE_FRAME"):
            _current_autofit_group(ws,tx)

    def test_current_autofit_group_frame_mismatch_rejected(self):
        ws=self._coversub_state_with_current_autofit_group()
        ws["source"]="0016-01-after"; ws["screenshot_sha256"]="b"*64
        ws["controls"]=self._current_group()
        ws["controls"][2]["frame_bbox"]=[71,27,1850,1053]
        tx={"selection_before_screenshot_sha256":"a"*64}
        with self.assertRaisesRegex(Exception,"FRAME_MISMATCH"):
            _current_autofit_group(ws,tx)

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
