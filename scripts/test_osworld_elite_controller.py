import unittest
from osworld_elite_controller import EliteController


class EliteControllerTests(unittest.TestCase):
    def test_failed_action_becomes_tabu_only_after_observed_no_progress(self):
        c=EliteController()
        cmd="pyautogui.click(100, 100)"
        self.assertTrue(c.before_action(cmd)['allow'])
        self.assertEqual(c.decision()['mode'],'fast')
        c.observe(False)
        self.assertFalse(c.before_action(cmd)['allow'])

    def test_progress_resets_stall_and_waits(self):
        c=EliteController(max_waits=2,max_stall=3)
        c.note_wait(); c.note_wait()
        self.assertEqual(c.decision()['mode'],'replan')
        c.before_action("pyautogui.press('esc')")
        c.observe(True)
        self.assertEqual(c.decision()['mode'],'fast')
        self.assertEqual(c.metrics()['waits'],0)

    def test_two_waits_force_replan(self):
        c=EliteController(max_waits=2)
        self.assertEqual(c.note_wait()['mode'],'fast')
        self.assertEqual(c.note_wait()['mode'],'replan')

    def test_latency_switches_fast_slow_replan(self):
        c=EliteController(fast_latency_s=8,hard_latency_s=20)
        self.assertEqual(c.record_latency(4)['mode'],'fast')
        self.assertEqual(c.record_latency(9)['mode'],'slow')
        self.assertEqual(c.record_latency(21)['mode'],'replan')

    def test_061_failure_pattern_is_cut_before_long_wait_loop(self):
        c=EliteController(max_waits=2,max_stall=3)
        # Historical failure: useful actions were followed by dozens of WAITs.
        for i in range(3):
            cmd=f"pyautogui.click({100+i}, {200+i})"
            self.assertTrue(c.before_action(cmd)['allow'])
            c.observe(True)
        waits=0
        for _ in range(60):
            waits+=1
            state=c.note_wait()
            if state['mode']=='replan':
                break
        self.assertEqual(waits,2)
        self.assertLess(waits,60)

    def test_no_progress_action_requires_different_strategy(self):
        c=EliteController(max_stall=3)
        failed="pyautogui.click(1049, 686)"
        c.before_action(failed); c.observe(False)
        self.assertFalse(c.before_action(failed)['allow'])
        self.assertTrue(c.before_action("pyautogui.hotkey('alt','tab')")['allow'])


if __name__=='__main__':
    unittest.main()
