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
        self.assertIn("pyautogui.press('/')", search['command'])
        self.assertIn("pyautogui.write('Sample Colorize'", search['command'])
        self.assertIn("pyautogui.sleep(1.0)", search['command'])
        self.assertTrue(search['command'].endswith("pyautogui.press('enter')"))
        self.assertEqual(search['checkpoint']['visible_text'], 'Get Sample Colors')
        self.assertEqual(search['specialist_phase'], 'open-colorize')

    def test_dialog_drives_sample_apply_close_in_order(self):
        obs = (frame('[IMG_7318_original] (imported)-1.0 - GIMP') + '\n'
               'push-button\tGet Sample Colors\tGet Sample Colors\tx\tx\t(300, 700)\t(120, 30)\n'
               'push-button\tApply\tApply\tx\tx\t(600, 700)\t(90, 30)\n'
               'push-button\tClose\tClose\tx\tx\t(700, 700)\t(90, 30)\n'
               'check-box\tUse subcolors\tUse subcolors\tx\tx\t(900,650)\t(120,20)\n'
               'check-box\tHold intensity\tHold intensity\tx\tx\t(500,650)\t(120,20)\n'
               'check-box\tOriginal intensity\tOriginal intensity\tx\tx\t(650,650)\t(140,20)')
        state = {'sample_loaded': True}
        a = next_recovery_action(TASK, APP, obs, state)
        self.assertEqual(a['target']['label'], 'Use subcolors')
        state['use_subcolors_enabled'] = True
        self.assertEqual(next_recovery_action(TASK, APP, obs, state)['target']['label'], 'Original intensity')
        state['original_intensity_disabled'] = True
        self.assertEqual(next_recovery_action(TASK, APP, obs, state)['target']['label'], 'Hold intensity')
        state['hold_intensity_disabled'] = True
        self.assertEqual(next_recovery_action(TASK, APP, obs, state)['target']['label'], 'Get Sample Colors')
        state['sample_colors_requested'] = True
        self.assertEqual(next_recovery_action(TASK, APP, obs, state)['target']['label'], 'Apply')
        state['colorize_applied'] = True
        self.assertEqual(next_recovery_action(TASK, APP, obs, state)['target']['label'], 'Close')

    def test_colorize_processing_cancel_is_never_clicked(self):
        obs = (frame('[IMG_7318_original] (imported)-1.0 - GIMP') + '\n'
               'push-button\tGet Sample Colors\tGet Sample Colors\tx\tx\t(300,700)\t(120,30)\n'
               'push-button\tApply\tApply\tx\tx\t(600,700)\t(90,30)\n'
               'push-button\tClose\tClose\tx\tx\t(700,700)\t(90,30)\n'
               'push-button\tCancel\tCancel\tx\tx\t(1632,1048)\t(74,29)')
        state = {'sample_loaded': True, 'owned': True, 'use_subcolors_enabled': True,
                 'hold_intensity_disabled': True, 'original_intensity_disabled': True,
                 'sample_colors_requested': True, 'colorize_applied': True}
        self.assertIsNone(next_recovery_action(TASK, APP, obs, state))
        self.assertTrue(state['colorize_processing'])
        settled = obs.replace('push-button\tCancel\tCancel\tx\tx\t(1632,1048)\t(74,29)', '')
        action = next_recovery_action(TASK, APP, settled, state)
        self.assertFalse(state['colorize_processing'])
        self.assertEqual(action['target']['label'], 'Close')

    def test_open_colorize_waits_for_delayed_accessibility_tree(self):
        target = frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        state = {'sample_loaded': True, 'owned': True, 'colorize_open_requested': True}
        self.assertIsNone(next_recovery_action(TASK, APP, target, state))
        self.assertEqual(state['colorize_open_waits'], 1)

    def test_closed_colorize_waits_for_dialog_disappearance(self):
        obs = (frame('[IMG_7318_original] (imported)-1.0 - GIMP') + '\n'
               'push-button\tGet Sample Colors\tGet Sample Colors\tx\tx\t(300,700)\t(120,30)\n'
               'push-button\tApply\tApply\tx\tx\t(600,700)\t(90,30)\n'
               'push-button\tClose\tClose\tx\tx\t(700,700)\t(90,30)')
        state = {'sample_loaded': True, 'owned': True, 'colorize_close_requested': True}
        self.assertIsNone(next_recovery_action(TASK, APP, obs, state))

    def test_official_tree_active_layer_recovers_sample_without_frame(self):
        obs = ('label\tIMG_7318_original.jpg (454.6 MB)\tx\n'
               'label\tIMG_7328_edited.jpg (454.6 MB)\tx\n'
               'table-cell\tIMG_7328_edited.jpg\tIMG_7328_edited.jpg\tx\tx\t(1846, 555)\t(128, 38)')
        a = next_recovery_action(TASK, APP, obs, {'sample_loaded': True, 'owned': True})
        self.assertEqual(a['command'], "pyautogui.hotkey('ctrl', 'pageup')")

    def test_export_sequence_stays_inside_specialist(self):
        target = frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        state = {'sample_loaded': True, 'owned': True, 'colorize_closed': True}
        baseline = next_recovery_action(TASK, APP, target, state)
        self.assertEqual(baseline['specialist_phase'], 'export-baseline')
        state['export_baseline_captured'] = True
        state['export_baseline_returned'] = True
        a = next_recovery_action(TASK, APP, target, state)
        self.assertEqual(a['specialist_phase'], 'export-open')
        dialog = target + '\ndialog\tExport Image\tExport Image\tx\npush-button\tExport\tExport\tx'
        state['export_open_requested'] = True
        a = next_recovery_action(TASK, APP, dialog, state)
        self.assertEqual(a['specialist_phase'], 'export-name-focus')
        self.assertEqual(a['command'], "pyautogui.hotkey('alt', 'n')")
        state['export_name_requested'] = True
        a = next_recovery_action(TASK, APP, dialog, state)
        self.assertEqual(a['specialist_phase'], 'export-name')
        self.assertIn('IMG_7318_edited.jpg', a['command'])
        state['export_name_typed'] = True
        a = next_recovery_action(TASK, APP, dialog, state)
        self.assertEqual(a['specialist_phase'], 'export-submit')
        self.assertEqual(a['target']['label'], 'Export')


    def test_jpeg_confirm_uses_button_inside_dialog_not_global_accelerator(self):
        target = frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        obs = (target + '\ndialog\tExport Image as JPEG\tExport Image as JPEG\tx\tx\t(992, 413)\t(314, 547)\n'
               'push-button\tExport\tExport\tx\tx\t(1209, 915)\t(85, 33)\n'
               'push-button\tExport\tExport\tx\tx\t(1551, 1030)\t(85, 33)')
        state = {'sample_loaded': True, 'owned': True, 'colorize_closed': True,
                 'export_baseline_captured': True, 'export_baseline_returned': True,
                 'export_open_requested': True, 'export_name_requested': True,
                 'export_name_typed': True, 'export_submitted': True}
        a = next_recovery_action(TASK, APP, obs, state)
        self.assertEqual(a['specialist_phase'], 'export-confirm')
        self.assertEqual(a['command'], 'pyautogui.click(1251, 931)')
        self.assertNotIn('hotkey', a['command'])

    def test_original_overwrite_modal_is_cancelled_fail_closed(self):
        target = frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        obs = (target + '\ndialog\tExport Image\tExport Image\tx\n'
               'label\tA file named "IMG_7318_original.jpg" already exists. Do you want to replace it?\tx\n'
               'push-button\tCancel\tCancel\tx')
        state = {'sample_loaded': True, 'owned': True, 'colorize_closed': True,
                 'export_baseline_captured': True, 'export_baseline_returned': True,
                 'export_open_requested': True, 'export_name_requested': True,
                 'export_name_typed': True, 'export_submitted': True}
        a = next_recovery_action(TASK, APP, obs, state)
        self.assertEqual(a['specialist_phase'], 'export-original-overwrite-cancel')
        self.assertEqual(a['target']['label'], 'Cancel')

    def test_missing_original_control_uses_bounded_dialog_accelerator(self):
        obs = (frame('[IMG_7318_original] (imported)-1.0 - GIMP') + '\n'
               'push-button\tGet Sample Colors\tGet Sample Colors\tx\tx\t(921,722)\t(148,33)\n'
               'push-button\tApply\tApply\tx\tx\t(1229,722)\t(148,33)\n'
               'push-button\tClose\tClose\tx\tx\t(1075,722)\t(148,33)\n'
               'check-box\tUse subcolors\tUse subcolors\tx\tx\t(1026,665)\t(118,21)\n'
               'check-box\tHold intensity\tHold intensity\tx\tx\t(613,665)\t(117,21)')
        state = {'sample_loaded': True, 'owned': True, 'use_subcolors_enabled': True}
        a = next_recovery_action(TASK, APP, obs, state)
        self.assertEqual(a['specialist_phase'], 'disable-original-intensity')
        self.assertEqual(a['command'], "pyautogui.hotkey('alt', 'n')")
        self.assertNotIn('target', a)

    def test_sample_colors_processing_holds_before_apply(self):
        obs = (frame('[IMG_7318_original] (imported)-1.0 - GIMP') + '\n'
               'push-button\tGet Sample Colors\tGet Sample Colors\tx\tx\t(921,722)\t(148,33)\n'
               'push-button\tApply\tApply\tx\tx\t(1229,722)\t(148,33)\n'
               'push-button\tClose\tClose\tx\tx\t(1075,722)\t(148,33)\n'
               'push-button\tCancel\tCancel\tx\tx\t(1632,1048)\t(74,29)')
        state = {'sample_loaded':True,'owned':True,'use_subcolors_enabled':True,
                 'original_intensity_disabled':True,'hold_intensity_disabled':True,
                 'sample_colors_requested':True}
        self.assertIsNone(next_recovery_action(TASK, APP, obs, state))
        self.assertTrue(state['sample_colors_processing'])

    def test_close_is_observed_before_export_opens(self):
        dialog = (frame('[IMG_7318_original] (imported)-1.0 - GIMP') + '\n'
                  'push-button\tGet Sample Colors\tGet Sample Colors\tx\n'
                  'push-button\tApply\tApply\tx\n'
                  'push-button\tClose\tClose\tx')
        state={'sample_loaded':True,'owned':True,'colorize_close_requested':True}
        self.assertIsNone(next_recovery_action(TASK, APP, dialog, state))
        target=frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        a=next_recovery_action(TASK, APP, target, state)
        self.assertTrue(state['colorize_closed'])
        self.assertEqual(a['specialist_phase'],'export-baseline')

    def test_export_confirm_waits_for_modal_and_processing_then_finishes(self):
        target=frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        state={'sample_loaded':True,'owned':True,'colorize_closed':True,
               'export_baseline_captured':True,'export_baseline_returned':True,
               'export_open_requested':True,'export_name_requested':True,
               'export_name_typed':True,'export_submitted':True,
               'export_confirm_requested':True}
        jpeg=target+'\ndialog\tExport Image as JPEG\tExport Image as JPEG\tx'
        self.assertIsNone(next_recovery_action(TASK, APP, jpeg, state))
        busy=target+'\npush-button\tCancel\tCancel\tx\tx\t(1632,1048)\t(74,29)'
        self.assertIsNone(next_recovery_action(TASK, APP, busy, state))
        self.assertTrue(state['export_processing'])
        verify=next_recovery_action(TASK, APP, target, state)
        self.assertEqual(verify['action'],'exec')
        self.assertEqual(verify['specialist_phase'],'verify-output-open')
        self.assertTrue(state['export_confirmed'])
        state['output_verify_open']=True
        chooser=(target+'\ntable-cell\tIMG_7318_edited.jpg\tIMG_7318_edited.jpg\tx\tx\t(200,200)\t(300,30)\n'
                 'push-button\tOpen\tOpen\tx\tx\t(976,704)\t(85,33)')
        verify_physical=next_recovery_action(TASK, APP, chooser, state)
        self.assertEqual(verify_physical['action'],'exec')
        self.assertEqual(verify_physical['specialist_phase'],'verify-output-physical')
        proven=('ARBM061_GIMP_EXPORT_PROVENANCE_SUCCESS size=4096 mtime_ns=999999999999999999 '
                'sha256=' + 'a'*64)
        done=next_recovery_action(TASK, APP, proven, state)
        self.assertEqual(done['action'],'finish')
        self.assertTrue(state['output_physical_provenance'])
        self.assertEqual(state['output_provenance_sha256'],'a'*64)


    def test_physical_provenance_failure_never_emits_finish(self):
        state={'sample_loaded':True,'owned':True,'colorize_closed':True,
               'export_baseline_captured':True,'export_baseline_returned':True,
               'export_open_requested':True,'export_name_requested':True,
               'export_name_typed':True,'export_submitted':True,
               'export_confirm_requested':True,'export_confirmed':True,
               'output_verify_open':True}
        failed='ARBM061_GIMP_EXPORT_PROVENANCE_FAIL PHYSICAL_FILE_UNPROVEN'
        self.assertIsNone(next_recovery_action(TASK, APP, failed, state))
        self.assertEqual(state['export_provenance_error'],'PHYSICAL_FILE_UNPROVEN')


    def test_profile_import_modal_clicks_convert_via_accessibility_target(self):
        obs = ("dialog\tImport Image from a Color Profile\tImport Image from a Color Profile\tx\tx\t(800,300)\t(600,400)\n"
               "label\tIMG_7318_original.jpg\tIMG_7318_original.jpg\tx\n"
               "push-button\tConvert\tConvert\tx\tx\t(1180,650)\t(100,34)")
        state = {'sample_loaded': True, 'owned': True}
        a = next_recovery_action(TASK, APP, obs, state)
        self.assertEqual(a['target'], {'source':'accessibility','label':'Convert','role':'push-button'})
        self.assertEqual(a['command'], 'pyautogui.click(0, 0)')
        self.assertEqual(a['specialist_phase'], 'convert-profile')
        self.assertFalse(state['profile_modal_error'])

    def test_live_vm_rgb_working_space_modal_clicks_convert(self):
        obs = ("dialog\tConvert to RGB Working Space?\tConvert to RGB Working Space?\tx\tx\t(752,300)\t(485,431)\n"
               "label\tConvert the image to the built-in sRGB color profile?\tConvert the image to the built-in sRGB color profile?\tx\n"
               "push-button\tConvert\tConvert\tx\tx\t(1140,686)\t(85,33)\n"
               "push-button\tKeep\tKeep\tx\tx\t(1049,686)\t(85,33)")
        state = {'sample_loaded': True, 'owned': True}
        a = next_recovery_action(TASK, APP, obs, state)
        self.assertEqual(a['target'], {'source':'accessibility','label':'Convert','role':'push-button'})
        self.assertEqual(a['specialist_phase'], 'convert-profile')

    def test_profile_import_modal_missing_convert_fails_closed_after_three_observations(self):
        obs = "dialog\tImport Image from a Color Profile\tImport Image from a Color Profile\tx\tx\t(800,300)\t(600,400)"
        state = {'sample_loaded': True, 'owned': True}
        self.assertIsNone(next_recovery_action(TASK, APP, obs, state))
        self.assertFalse(state['profile_modal_error'])
        self.assertIsNone(next_recovery_action(TASK, APP, obs, state))
        self.assertFalse(state['profile_modal_error'])
        self.assertIsNone(next_recovery_action(TASK, APP, obs, state))
        self.assertTrue(state['profile_modal_error'])
        clear = frame('[IMG_7318_original] (imported)-1.0 - GIMP')
        next_recovery_action(TASK, APP, clear, state)
        self.assertFalse(state['profile_modal_error'])
        self.assertEqual(state['profile_modal_missing_convert_waits'], 0)


if __name__ == '__main__':
    unittest.main()
