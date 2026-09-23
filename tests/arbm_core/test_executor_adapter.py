import unittest
from unittest.mock import patch
from arbm_core.action_ir import ActionIR, ActionKind, TargetRef
from arbm_core.executor_adapter import LegacyExecutorAdapter, LegacyObservationAdapter

class ExecutorAdapterTests(unittest.TestCase):
    def target(self, **attrs):
        base={"label":"Save","role":"push-button"}
        base.update(attrs)
        return TargetRef("app.save","accessibility","v1",base)

    def test_type_text_compiles_through_osworld_control(self):
        action=ActionIR(
            ActionKind.TYPE_TEXT,
            TargetRef("field.name","accessibility","v1",{"label":"Name","role":"entry"}),
            {"text":"hello"},
            ("field.name grounded",),
            ("field.name=='hello'",),
            metadata={"plan":"type into Name"},
        )
        observation="entry\tName\t\t\t\t10,20\t120x30"
        adapter=LegacyExecutorAdapter(active_application="WPS Presentation",observation_text=observation)
        out=adapter.compile(action)
        self.assertEqual(out.legacy_action["action"],"exec")
        self.assertIn("pyautogui.write('hello'",out.legacy_action["command"])

    def test_accessibility_click_is_re_grounded_not_coordinate_trusted(self):
        action=ActionIR(
            ActionKind.CLICK,self.target(),{"x":999,"y":999,"clicks":1},
            ("save grounded",),("save dialog changed",),
            metadata={"plan":"click Save"},
        )
        observation="push-button\tSave\t\t\t\t100,200\t80x30"
        out=LegacyExecutorAdapter(
            active_application="WPS Presentation",observation_text=observation
        ).compile(action)
        self.assertIn("pyautogui.click(140, 215",out.legacy_action["command"])
        self.assertNotIn("999",out.legacy_action["command"])

    def test_unsafe_terminal_hotkey_is_rejected_by_existing_compiler(self):
        action=ActionIR(
            ActionKind.HOTKEY,
            TargetRef("app","accessibility","v1",{"label":"App","role":"section"}),
            {"keys":["ctrl","alt","t"]},
            ("app grounded",),("terminal opened",),
        )
        with self.assertRaises(ValueError):
            LegacyExecutorAdapter(active_application="Desktop").compile(action)

    def test_canonical_pointer_requires_explicit_allowance(self):
        action=ActionIR(
            ActionKind.CLICK,
            TargetRef("shape16","task091-pptx-canonical","v1",
                      {"cx":100,"cy":200,"slide":3,"shape_id":16,
                       "proof_sha256":"a"*64,"foreground_sha256":"b"*64,
                       "deck_sha256":"c"*64}),
            {"x":100,"y":200},
            ("shape grounded",),("shape selected",),
        )
        with self.assertRaises(ValueError):
            LegacyExecutorAdapter(active_application="WPS Presentation",allow_canonical=False).compile(action)

    def test_executor_returns_compiled_evidence(self):
        action=ActionIR(
            ActionKind.TYPE_TEXT,
            TargetRef("field.name","accessibility","v1",{"label":"Name","role":"entry"}),
            {"text":"x"},("grounded",),("changed",),
        )
        observation="entry\tName\t\t\t\t10,20\t120x30"
        adapter=LegacyExecutorAdapter(active_application="WPS Presentation",observation_text=observation)
        result=adapter.executor(lambda a:{"sent":True})(action)
        self.assertTrue(result["sent"])
        self.assertEqual(len(result["action_digest"]),64)
        self.assertIn("compiled_action",result)

class ObservationAdapterTests(unittest.TestCase):
    def test_legacy_observation_becomes_world(self):
        obs={"deck_file":{"sha256":"a"*64},"deck_slide_shapes":{"3":[
            {"id":1,"kind":"shape","name":"Title","text":"Hello","geometry":{}}
        ]}}
        world=LegacyObservationAdapter(lambda:obs).observe_world()
        self.assertEqual(world.require_entity("deck.slide3.shape.Title").attributes["text"],"Hello")

if __name__=="__main__":
    unittest.main()