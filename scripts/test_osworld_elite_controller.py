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

    def test_failed_action_allows_exactly_one_evidence_bounded_retry(self):
        c=EliteController()
        cmd="pyautogui.press('esc')"
        self.assertTrue(c.before_action(cmd)['allow'])
        c.observe(False)
        proof={'fresh_observation':True,'state_changed':True,'bounded_retry':True,
               'reason':'foreground changed while stacked modal remains'}
        admitted=c.before_action(cmd,retry_proof=proof)
        self.assertTrue(admitted['allow'])
        self.assertEqual(admitted['reason'],'evidence_bounded_retry')
        c.observe(False)
        self.assertFalse(c.before_action(cmd,retry_proof=proof)['allow'])
        self.assertEqual(c.metrics()['evidence_bounded_retries'],1)

    def test_incomplete_retry_proof_never_bypasses_tabu(self):
        c=EliteController()
        cmd="pyautogui.press('esc')"
        c.before_action(cmd); c.observe(False)
        for proof in (
            None,
            {},
            {'fresh_observation':True,'state_changed':False,'bounded_retry':True,'reason':'x'},
            {'fresh_observation':True,'state_changed':True,'bounded_retry':False,'reason':'x'},
            {'fresh_observation':True,'state_changed':True,'bounded_retry':True,'reason':''},
        ):
            self.assertFalse(c.before_action(cmd,retry_proof=proof)['allow'])

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


    def test_checkpoint_backtrack_anchor_is_verified_state_only(self):
        c=EliteController(max_stall=2)
        proof={'name':'Reference opened','application':'GIMP','visible_text':'IMG_7328_edited.jpg','observation_sha256':'abc123'}
        anchor=c.checkpoint(proof)
        self.assertEqual(anchor['checkpoint_count'],1)
        self.assertEqual(anchor['last_verified_checkpoint']['application'],'GIMP')
        c.before_action("pyautogui.press('x')"); c.observe(False)
        c.before_action("pyautogui.press('y')"); decision=c.observe(False)
        self.assertEqual(decision['mode'],'replan')
        self.assertEqual(decision['reason'],'checkpoint_backtrack')
        self.assertEqual(c.metrics()['backtrack_events'],1)

    def test_invalid_checkpoint_is_not_admitted(self):
        c=EliteController()
        c.checkpoint({'name':'x','application':'','visible_text':''})
        self.assertEqual(c.metrics()['verified_checkpoints'],0)


if __name__=='__main__':
    unittest.main()
