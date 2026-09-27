"""Regression cases for the real WPS coordinate and evidence failures."""
import ast
import copy
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw
from arbm091.semantic_runtime import _verify_text_transaction_for_mode, next_text_action
from arbm091.semantic_transaction import SemanticTransactionError


class CriticalPersistenceTests(unittest.TestCase):
    def state(self):
        return {
            "screen":[0,0,1920,1080],
            "window":{"bbox":[70,27,1850,1053]},
            "active_slide":2,
            "deck_file":{"sha256":"a"*64,"slide_size":{"w":1600,"h":900}},
            "slide_canvas_bbox":[443,194,1413,795],
            "screenshot_sha256":"b"*64,
            "deck_slide_shapes":{"2":[
                {"kind":"shape","id":15,"name":"SummaryArr_Value","text":"$42.8M",
                 "geometry":{"x":130,"y":250,"w":180,"h":50},"font_sizes":[2400]},
                {"kind":"shape","id":14,"name":"SummaryArr_Label","text":"ARR exit target",
                 "geometry":{"x":130,"y":200,"w":180,"h":30},"font_sizes":[1100]},
            ]},
        }

    @patch.dict(os.environ,{"TASK_ID":"091"})
    def test_full_width_canvas_is_not_clipped_at_1670(self):
        source=ast.parse(Path("scripts/arbm091/guest_probe.py").read_text())
        node=next(n for n in source.body if isinstance(n,ast.FunctionDef)
                  and n.name=="_task091_slide_canvas_bbox")
        scope={"os":os}
        exec(compile(ast.Module(body=[node],type_ignores=[]),"<canvas>","exec"),scope)
        for left,top,width in ((443,194,1413),(350,263,1137)):
            image=Image.new("RGB",(1920,1080),"white")
            ImageDraw.Draw(image).rectangle((left,top,left+width-1,top+60),fill=(22,43,67))
            result=scope["_task091_slide_canvas_bbox"](image,{"slide_size":{"w":1600,"h":900}})
            self.assertEqual(result,[left,top,width,round(width*900/1600)])

    @patch.dict(os.environ,{"TASK091_CRITICAL_ERROR_ONLY":"1"})
    def test_critical_requires_complete_target_only_diff(self):
        before=self.state()
        after=copy.deepcopy(before)
        after["deck_slide_shapes"]["2"][0]["text"]="$40.9M"
        verdict=_verify_text_transaction_for_mode(before,after,(2,"shape",15,"SummaryArr_Value"),"$40.9M")
        self.assertIs(verdict["no_collateral_mutation"],True)
        after["deck_slide_shapes"]["2"].pop()
        with self.assertRaises(SemanticTransactionError):
            _verify_text_transaction_for_mode(before,after,(2,"shape",15,"SummaryArr_Value"),"$40.9M")

    @patch.dict(os.environ,{"TASK091_CRITICAL_ERROR_ONLY":"1"})
    def test_reobserve_layout_and_never_toggle_f2_after_double_click(self):
        ws=self.state()
        state={"slide":2}
        plan=((2,0,0,"$42.8M","$40.9M"),)
        next_text_action(state,ws,plan)
        ws["slide_canvas_bbox"]=[350,263,1137,640]
        action=next_text_action(state,ws,plan)
        self.assertEqual(action["specialist_phase"],"critical-summaryarr-enter-text")
        action=next_text_action(state,ws,plan)
        self.assertNotIn("f2",action["command"])
        self.assertNotIn("backspace",action["command"])
        self.assertIn("ctrl', 's",action["command"])

    @patch.dict(os.environ,{"TASK091_CRITICAL_ERROR_ONLY":"1"})
    def test_layout_drift_after_text_entry_blocks_mutation(self):
        ws=self.state()
        state={"slide":2}
        plan=((2,0,0,"$42.8M","$40.9M"),)
        next_text_action(state,ws,plan)
        next_text_action(state,ws,plan)
        ws["slide_canvas_bbox"]=[350,263,1137,640]
        action=next_text_action(state,ws,plan)
        self.assertEqual(action["action"],"terminal")
        self.assertEqual(action["reason"],"TASK091_TEXT_EDIT_CANVAS_DRIFT")

if __name__=="__main__":
    unittest.main()
