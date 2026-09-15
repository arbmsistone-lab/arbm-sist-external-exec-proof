import pathlib, sys, unittest
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from osworld_gimp_style_transfer import parse_reference_pair_task, next_recovery_action

TASK = ("I have seen an example of how IMG_7328_original.jpg was processed to produce "
        "IMG_7328_edited.jpg by applying certain edits and styles in color grading. "
        "Apply the same style/edits to IMG_7318_original.jpg. Save the result as "
        "IMG_7318_edited.jpg in ~/Pictures.")
APP = 'GNU Image Manipulation Program'


def frame(name):
    return 'frame\t%s\tx\tx\tx\t(0, 20)\t(1500, 900)' % name


class GimpStyleTransferTests(unittest.TestCase):
    def test_parses_reference_pair_without_task_id(self):
        p = parse_reference_pair_task(TASK)
        self.assertEqual(p['reference_edited'], 'IMG_7328_edited.jpg')
        self.assertEqual(p['target_original'], 'IMG_7318_original.jpg')
        self.assertEqual(p['output'], 'IMG_7318_edited.jpg')

    def test_unrelated_image_task_is_not_admitted(self):
        self.assertIsNone(parse_reference_pair_task('Crop photo.jpg and save output.jpg'))

    def test_wrong_application_never_drives_gui(self):
        self.assertIsNone(next_recovery_action(TASK, 'Files', 'menu\tColors\tColors', {}))

    def test_profile_dialog_prefers_keep_with_positive_checkpoint(self):
        obs = ("label\tThe image 'IMG_7318_original.jpg' has an embedded color profile\tx\n"
               "push-button\tKeep\tKeep\tx\tx\t(1049, 686)\t(85, 33)")
        a = next_recovery_action(TASK, APP, obs, {})
        self.assertEqual(a['target']['label'], 'Keep')
        self.assertEqual(a['checkpoint']['visible_text'], 'IMG_7318_original.jpg (')

    def test_file_chooser_double_clicks_exact_reference_atomically(self):
        obs = ("table-cell\tIMG_7318_original.jpg\tx\tx\tx\t(100, 100)\t(300, 30)\n"
               "table-cell\tIMG_7328_edited.jpg\tx\tx\tx\t(100, 140)\t(300, 30)\n"
               "push-button\tOpen\tOpen\tx\tx\t(976, 704)\t(85, 33)")
        a = next_recovery_action(TASK, APP, obs, {})
        self.assertEqual(a['target']['label'], 'IMG_7328_edited.jpg')
        self.assertEqual(a['command'], 'pyautogui.doubleClick(0, 0)')
        self.assertIsNone(a['checkpoint'])
        self.assertEqual(a['specialist_phase'], 'open-sample')

    def test_background_tab_label_does_not_fake_active_document(self):
        obs = (frame('[IMG_7328_edited] (imported)-2 - GIMP') + '\n' +
               'label\tIMG_7318_original.jpg (454.6 MB)\tx')
        a = next_recovery_action(TASK, APP, obs, {'sample_loaded': True})
        self.assertEqual(a['command'], "pyautogui.hotkey('ctrl', 'pageup')")

    def test_action_search_is_single_gui_call_then_enter(self):
        target_obs = frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        state = {'sample_loaded': True}
        search = next_recovery_action(TASK, APP, target_obs, state)
        self.assertEqual(search['command'], "pyautogui.write('/Sample Colorize', interval=0.04)")
        self.assertNotIn(';', search['command'])
        self.assertEqual(search['checkpoint']['visible_text'], 'Sample Colorize')

        result_obs = target_obs + '\nmenu-item\tSample Colorize\tSample Colorize\tx\tx\t(200, 200)\t(200, 30)'
        enter = next_recovery_action(TASK, APP, result_obs, state)
        self.assertEqual(enter['command'], "pyautogui.press('enter')")
        self.assertEqual(enter['checkpoint']['visible_text'], 'Get Sample Colors')

    def test_dialog_drives_sample_apply_close_in_order(self):
        obs = (frame('[IMG_7318_original] (imported)-1.0 - GIMP') + '\n'
               'dialog\tSample Colorize\tSample Colorize\tx\tx\t(200, 200)\t(800, 600)\n'
               'push-button\tGet Sample Colors\tGet Sample Colors\tx\tx\t(300, 700)\t(120, 30)\n'
               'push-button\tApply\tApply\tx\tx\t(600, 700)\t(90, 30)\n'
               'push-button\tClose\tClose\tx\tx\t(700, 700)\t(90, 30)')
        a = next_recovery_action(TASK, APP, obs, {'sample_loaded': True})
        self.assertEqual(a['target']['label'], 'Get Sample Colors')
        a = next_recovery_action(TASK, APP, obs, {'sample_loaded': True, 'sample_colors_requested': True})
        self.assertEqual(a['target']['label'], 'Apply')
        a = next_recovery_action(TASK, APP, obs, {'sample_loaded': True, 'sample_colors_requested': True, 'colorize_applied': True})
        self.assertEqual(a['target']['label'], 'Close')

    def test_official_tree_active_layer_recovers_sample_without_frame(self):
        obs = ('label\tIMG_7318_original.jpg (454.6 MB)\tx\n'
               'label\tIMG_7328_edited.jpg (454.6 MB)\tx\n'
               'table-cell\tIMG_7328_edited.jpg\tIMG_7328_edited.jpg\tx\tx\t(1846, 555)\t(128, 38)')
        a = next_recovery_action(TASK, APP, obs, {'sample_loaded': True, 'owned': True})
        self.assertEqual(a['command'], "pyautogui.hotkey('ctrl', 'pageup')")

    def test_export_sequence_stays_inside_specialist(self):
        target = frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        state = {'sample_loaded': True, 'owned': True, 'colorize_closed': True}
        a = next_recovery_action(TASK, APP, target, state)
        self.assertEqual(a['specialist_phase'], 'export-open')
        dialog = target + '\ndialog\tExport Image\tExport Image\tx'
        state['export_open_requested'] = True
        a = next_recovery_action(TASK, APP, dialog, state)
        self.assertEqual(a['specialist_phase'], 'export-location')
        state['export_location_requested'] = True
        a = next_recovery_action(TASK, APP, dialog, state)
        self.assertIn('/home/user/Pictures/IMG_7318_edited.jpg', a['command'])


if __name__ == '__main__':
    unittest.main()
