import pathlib, sys, unittest
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from osworld_gimp_sample_probe import gimp_visible, active_gimp_document, target_loaded, TARGET, tabular_accessibility

DOCK_ONLY = """<root><application name="gnome-shell"><push-button name="GNU Image Manipulation Program" visible="true"/></application></root>"""
CHOOSER = """<root><application name="gnome-shell"><push-button name="GNU Image Manipulation Program" visible="true"/><table-cell name="IMG_7318_original.jpg"/><push-button name="Open"/></application></root>"""
ACTIVE = """<root><application name="gimp"/><frame name="[IMG_7318_original] (imported)-1.0 - GIMP" active="true" showing="true" visible="true"/></root>"""
SAMPLE = """<root><application name="gimp"/><frame name="[IMG_7328_edited] (imported)-2.0 - GIMP" active="true" showing="true" visible="true"/></root>"""

class ProbeStateTests(unittest.TestCase):
    def test_dock_launcher_is_not_a_gimp_window(self):
        self.assertFalse(gimp_visible(DOCK_ONLY))
        self.assertFalse(target_loaded(DOCK_ONLY))

    def test_chooser_filename_does_not_fake_loaded_document(self):
        self.assertFalse(gimp_visible(CHOOSER))
        self.assertFalse(target_loaded(CHOOSER))

    def test_active_gimp_frame_proves_target(self):
        self.assertTrue(gimp_visible(ACTIVE))
        self.assertTrue(active_gimp_document(ACTIVE, TARGET))
        self.assertTrue(target_loaded(ACTIVE))

    def test_profile_modal_xml_converts_to_real_tabular_contract(self):
        xml = ("<root><dialog name='Import Image from a Color Profile' cp:screencoord='(800,300)' cp:size='(600,400)' xmlns:cp='urn:cp'>"
               "<push-button name='Convert' cp:screencoord='(1180,650)' cp:size='(100,34)'/></dialog></root>")
        tab = tabular_accessibility(xml)
        self.assertIn('dialog\tImport Image from a Color Profile', tab)
        self.assertIn('push-button\tConvert', tab)

    def test_active_sample_is_distinct_from_target(self):
        self.assertTrue(gimp_visible(SAMPLE))
        self.assertTrue(active_gimp_document(SAMPLE, 'IMG_7328_edited.jpg'))
        self.assertFalse(target_loaded(SAMPLE))

if __name__ == '__main__':
    unittest.main()
