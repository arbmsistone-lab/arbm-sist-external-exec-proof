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
        self.assertIn("pyautogui.write('/Sample Colorize'", result)
        self.assertEqual(shim.STATE['history'][-1]['source'], 'gimp-specialist')
        self.assertIsNotNone(shim.MILESTONES.pending)
        self.assertEqual(shim.MILESTONES.pending['predicate']['visible_text'], 'Sample Colorize')

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


if __name__ == '__main__':
    unittest.main()
