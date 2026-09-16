import pathlib, sys, unittest
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from osworld_061_calibrated_grade import next_calibrated_action
TASK=("I have seen an example of how IMG_7328_original.jpg was processed to produce IMG_7328_edited.jpg. "
      "Apply the same style/edits to IMG_7318_original.jpg. Save the result as IMG_7318_edited.jpg in ~/Pictures.")
GENERIC=("I have seen an example of how ref_original.jpg was processed to produce ref_edited.jpg. "
         "Apply the same style to target_original.jpg and save as target_edited.jpg.")
class Calibrated061Tests(unittest.TestCase):
    def test_reference_pair_admitted(self):
        a=next_calibrated_action(TASK,'GNU Image Manipulation Program','',{})
        self.assertEqual(a['specialist_phase'],'061-terminal-visible')
    def test_generic_reference_pair_admitted(self):
        a=next_calibrated_action(GENERIC,'Files','',{})
        self.assertEqual(a['specialist_phase'],'061-terminal-visible')
    def test_unrelated_pair_not_admitted(self):
        self.assertIsNone(next_calibrated_action('Edit a.jpg into b.jpg','GIMP','',{}))
    def test_unsafe_marker_falls_back(self):
        st={}; a=next_calibrated_action(TASK,'Terminal','ARBM061_REF_MODEL_UNSAFE rmse=22.1',st)
        self.assertEqual(a['specialist_phase'],'061-calibration-fallback'); self.assertTrue(st['fallback_requested'])
    def test_output_preexistence_hard_fails(self):
        st={'owned':True}; a=next_calibrated_action(TASK,'Terminal','ARBM061_OUTPUT_PREEXISTED',st)
        self.assertIsNone(a); self.assertEqual(st['hard_fail'],'OUTPUT_PREEXISTED')
    def test_timeout_is_bounded(self):
        st={'owned':True,'launch_requested':True,'script_requested':True,'run_requested':True,'run_waits':12}
        a=next_calibrated_action(TASK,'Terminal','',st)
        self.assertEqual(a['specialist_phase'],'061-calibration-timeout')
    def test_done_marker_finishes(self):
        st={}
        obs='ARBM061_DONE rmse=19.9000 model=poly3_residual size=6048x8064 sha256='+'a'*64+' bytes=123456'
        a=next_calibrated_action(TASK,'Terminal',obs,st)
        self.assertEqual(a['action'],'finish'); self.assertEqual(st['reference_rmse'],19.9)
if __name__=='__main__': unittest.main()
