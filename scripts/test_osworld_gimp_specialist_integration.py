import pathlib, sys, unittest
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import osworld_free_mesh_shim as shim
from osworld_control import Verifier
from osworld_milestones import Milestones
from osworld_elite_controller import EliteController

TASK = ("I have seen an example of how IMG_7328_original.jpg was processed to produce "
        "IMG_7328_edited.jpg by applying certain edits and styles in color grading. "
        "Apply the same style/edits to IMG_7318_original.jpg. Save the result as "
        "IMG_7318_edited.jpg in ~/Pictures.")
APP = 'GNU Image Manipulation Program'


def frame(name):
    return 'frame\t%s\tx\tx\tx\t(0, 20)\t(1500, 900)' % name


class GimpSpecialistIntegrationTests(unittest.TestCase):
    def setUp(self):
        shim.STATE.update({'history': [], 'executed': 0, 'previous': '', 'plan': '',
                           'wait_responses': 0, 'provider_waits': 0,
                           'gimp_specialist': {'sample_loaded': True}})
        shim.VERIFIER = Verifier()
        shim.MILESTONES = Milestones()
        shim.ELITE = EliteController(fast_latency_s=8, hard_latency_s=20,
                                     max_waits=2, max_stall=3)

    def body(self, app=APP):
        return {'instruction': TASK, 'active_application': app,
                'verified_milestones': [], 'phase': 'execute'}

    def test_search_action_passes_normal_policy_and_milestone_path(self):
        obs = frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        result = shim.try_gimp_specialist(self.body(), obs, obs)
        self.assertIn("pyautogui.press('/')", result)
        self.assertIn("pyautogui.write('Sample Colorize'", result)
        self.assertNotIn("pyautogui.write('/Sample Colorize'", result)
        self.assertIn("pyautogui.sleep(1.0)", result)
        self.assertIn("pyautogui.press('enter')", result)
        self.assertLess(result.index("pyautogui.write('Sample Colorize'"), result.index("pyautogui.press('enter')"))
        self.assertEqual(shim.STATE['history'][-1]['source'], 'gimp-specialist')
        self.assertIsNotNone(shim.MILESTONES.pending)
        self.assertEqual(shim.MILESTONES.pending['predicate']['visible_text'], 'Get Sample Colors')

    def test_atomic_open_owns_and_waits_for_delayed_dialog_tree(self):
        obs = frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        first = shim.try_gimp_specialist(self.body(), obs, obs)
        self.assertIn("pyautogui.press('/')", first)
        self.assertTrue(shim.STATE['gimp_specialist']['colorize_open_requested'])
        history_len = len(shim.STATE['history'])
        self.assertEqual(shim.try_gimp_specialist(self.body(), obs, obs), 'WAIT')
        self.assertEqual(len(shim.STATE['history']), history_len)

    def test_wrong_app_does_not_activate_specialist(self):
        obs = frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        self.assertIsNone(shim.try_gimp_specialist(self.body('Files'), obs, obs))
        self.assertEqual(shim.STATE['history'], [])

    def test_accessibility_pointer_is_compiled_before_issue(self):
        shim.STATE['gimp_specialist'] = {}
        obs = ("table-cell\tIMG_7328_edited.jpg\tx\tx\tx\t(100, 140)\t(300, 30)\n"
               "push-button\tOpen\tOpen\tx\tx\t(976, 704)\t(85, 33)")
        result = shim.try_gimp_specialist(self.body(), obs, obs)
        self.assertIn('pyautogui.doubleClick(250, 155)', result)
        self.assertNotIn('doubleClick(0, 0)', result)

    def test_dialog_internal_action_has_no_false_semantic_pending(self):
        shim.STATE['gimp_specialist'] = {'sample_loaded': True, 'owned': True}
        obs = ('push-button\tGet Sample Colors\tGet Sample Colors\tx\tx\t(300,700)\t(120,30)\n'
               'push-button\tApply\tApply\tx\tx\t(600,700)\t(90,30)\n'
               'push-button\tClose\tClose\tx\tx\t(700,700)\t(90,30)\n'
               'check-box\tUse subcolors\tUse subcolors\tx\tx\t(900,650)\t(120,20)\n'
               'check-box\tHold intensity\tHold intensity\tx\tx\t(500,650)\t(120,20)\n'
               'check-box\tOriginal intensity\tOriginal intensity\tx\tx\t(650,650)\t(140,20)')
        result = shim.try_gimp_specialist(self.body(), obs, obs)
        self.assertIn('pyautogui.click', result)
        self.assertTrue(shim.STATE['gimp_specialist']['use_subcolors_enabled'])
        self.assertIsNone(shim.MILESTONES.pending)

    def test_owned_specialist_holds_unknown_intermediate_state(self):
        shim.STATE['gimp_specialist'] = {'sample_loaded': True, 'owned': True}
        obs = 'label\tTransient GIMP state\tx'
        self.assertEqual(shim.try_gimp_specialist(self.body(), obs, obs), 'WAIT')
        self.assertEqual(shim.STATE['gimp_specialist']['uncertain_turns'], 1)

    def test_owned_specialist_never_falls_through_after_repeated_uncertainty(self):
        shim.STATE['gimp_specialist'] = {'sample_loaded': True, 'owned': True}
        obs = 'label\tTransient GIMP state\tx'
        for _ in range(6):
            self.assertEqual(shim.try_gimp_specialist(self.body(), obs, obs), 'WAIT')
        self.assertEqual(shim.STATE['gimp_specialist']['uncertain_turns'], 6)

    def test_owned_loop_rejection_never_falls_through(self):
        shim.STATE['gimp_specialist']={'sample_loaded':True,'owned':True}
        obs=frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        candidate={'action':'exec','command':"pyautogui.hotkey('ctrl','o')",'plan':'x',
                   'summary':'x','expected_change':'x','confidence':1.0,
                   'observed_facts':[],'verification':'x','checkpoint':None}
        from unittest.mock import patch
        with patch.object(shim,'next_recovery_action',return_value=candidate), \
             patch.object(shim,'ground_action',return_value=candidate), \
             patch.object(shim,'apply_live_policy',return_value={'kind':shim.DecisionKind.EXEC.value}), \
             patch.object(shim,'rejects_visual_navigation_loop',return_value=True):
            self.assertEqual(shim.try_gimp_specialist(self.body(),obs,obs),'WAIT')

    def test_specialist_finish_ignores_stale_global_milestone_stall(self):
        shim.STATE['gimp_specialist']={'sample_loaded':True,'owned':True,
            'colorize_closed':True,'export_confirmed':True}
        obs=(frame('[IMG_7318_original] (imported)-1.0 - GIMP') + '\n'
             'label\tIMG_7318_original.jpg (454.6 MB)\tIMG_7318_original.jpg (454.6 MB)')
        action={'action':'finish','command':'','plan':'done','summary':'done','confidence':1.0,
                'verification':'IMG_7318_original.jpg active after JPEG export confirmation'}
        shim.MILESTONES.stalled=3
        shim.VERIFIER.changes=1; shim.VERIFIER.no_progress=0
        from unittest.mock import patch
        with patch.object(shim,'next_recovery_action',return_value=action), \
             patch.object(shim,'ground_action',return_value=action), \
             patch.object(shim,'apply_live_policy',return_value={'kind':shim.DecisionKind.FINISH_CANDIDATE.value}):
            self.assertEqual(shim.try_gimp_specialist(self.body(),obs,obs),'DONE')


if __name__ == '__main__':
    unittest.main()
