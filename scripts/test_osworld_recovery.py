import unittest
from osworld_recovery import is_visual_task, recovery_policy, semantic_terminal


class RecoveryPolicyTests(unittest.TestCase):
    def test_visual_task_never_forces_text_route_on_semantic_stall(self):
        p = recovery_policy('Edit IMG_7318_original.jpg in GIMP', 'GNU Image Manipulation Program', 8, 0, 0, '')
        self.assertTrue(p['visual_task'])
        self.assertEqual(p['provider_hint'], 'openrouter')
        self.assertIn('Keep screenshot reasoning', p['strategy'])

    def test_nonvisual_stall_preserves_text_recovery(self):
        p = recovery_policy('Read a document and enter the rows', 'LibreOffice Writer', 8, 0, 0, '')
        self.assertFalse(p['visual_task'])
        self.assertEqual(p['provider_hint'], 'text')

    def test_semantic_stall_alone_cannot_terminate_active_gui(self):
        self.assertFalse(semantic_terminal(16, 0))
        self.assertFalse(semantic_terminal(24, 5))
        self.assertTrue(semantic_terminal(24, 6))

    def test_visual_detection_uses_foreground_app(self):
        self.assertTrue(is_visual_task('Match the reference style', 'darktable'))


if __name__ == '__main__':
    unittest.main()
