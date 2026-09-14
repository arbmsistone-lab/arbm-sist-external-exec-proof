import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from osworld_gimp_style_transfer import parse_reference_pair_task,next_recovery_action

TASK=("I have seen an example of how IMG_7328_original.jpg was processed to produce "
      "IMG_7328_edited.jpg by applying certain edits and styles in color grading. "
      "Apply the same style/edits to IMG_7318_original.jpg. Save the result as "
      "IMG_7318_edited.jpg in ~/Pictures.")

class GimpStyleTransferTests(unittest.TestCase):
 def test_parses_reference_pair_without_task_id(self):
  p=parse_reference_pair_task(TASK)
  self.assertEqual(p['reference_edited'],'IMG_7328_edited.jpg')
  self.assertEqual(p['target_original'],'IMG_7318_original.jpg')
  self.assertEqual(p['output'],'IMG_7318_edited.jpg')
 def test_unrelated_image_task_is_not_admitted(self):
  self.assertIsNone(parse_reference_pair_task('Crop photo.jpg and save output.jpg'))
 def test_wrong_application_never_drives_gui(self):
  self.assertIsNone(next_recovery_action(TASK,'Files','menu\tColors\tColors',{}))
 def test_profile_dialog_prefers_keep(self):
  obs=("label\tThe image 'IMG_7318_original.jpg' has an embedded color profile\tX\n"
       "push-button\tKeep\tKeep\t\t\t(1049, 686)\t(85, 33)")
  a=next_recovery_action(TASK,'GNU Image Manipulation Program',obs,{})
  self.assertEqual(a['target']['label'],'Keep')
 def test_real_file_chooser_selects_then_opens_sample(self):
  obs=("table-cell\tIMG_7318_original.jpg\tIMG_7318_original.jpg\n"
       "table-cell\tIMG_7328_edited.jpg\tIMG_7328_edited.jpg\n"
       "table-cell\tIMG_7328_original.jpg\tIMG_7328_original.jpg\n"
       "push-button\tOpen\tOpen\t\t\t(976, 704)\t(85, 33)")
  state={}
  first=next_recovery_action(TASK,'GNU Image Manipulation Program',obs,state)
  second=next_recovery_action(TASK,'GNU Image Manipulation Program',obs,state)
  self.assertEqual(first['target']['label'],'IMG_7328_edited.jpg')
  self.assertEqual(second['target']['label'],'Open')
 def test_colors_map_sample_colorize_requires_visible_controls(self):
  state={'sample_loaded':True,'target_active':True}
  a=next_recovery_action(TASK,'GNU Image Manipulation Program','menu\tColors\tColors',state)
  self.assertEqual(a['target']['label'],'Colors')
  a=next_recovery_action(TASK,'GNU Image Manipulation Program','menu-item\tMap\tMap',state)
  self.assertEqual(a['target']['label'],'Map')
  a=next_recovery_action(TASK,'GNU Image Manipulation Program','menu-item\tSample Colorize\tSample Colorize',state)
  self.assertEqual(a['target']['label'],'Sample Colorize')

if __name__=='__main__':unittest.main()
