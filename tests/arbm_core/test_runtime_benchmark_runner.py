import unittest
from arbm_core.benchmark_program import build_internal_catalog
from arbm_core.runtime_benchmark_runner import run_task

class RuntimeBenchmarkRunnerTests(unittest.TestCase):
    def by_domain(self,domain):
        return next(t for t in build_internal_catalog(40) if t.domain==domain)

    def test_standard_domain_runs_real_runtime(self):
        row=run_task(self.by_domain("gui"),1)
        self.assertTrue(row["success"])
        self.assertEqual(row["cost_usd"],0.0)
        self.assertEqual(row["terminal_code"],"PASS")
        self.assertGreaterEqual(row["steps"],1)

    def test_adversarial_conflict_fails_closed_as_safe_success(self):
        task=next(t for t in build_internal_catalog(88)
                  if t.domain=="adversarial" and t.seed % 11 == 0)
        row=run_task(task,1)
        self.assertTrue(row["success"])
        self.assertTrue(row["recovered"])
        self.assertEqual(row["terminal_code"],"RECOVERY_CONFLICT_FAIL_CLOSED")

    def test_recovery_domain_gets_bounded_second_attempt(self):
        task=next(t for t in build_internal_catalog(24)
                  if t.domain=="recovery" and t.seed % 3 == 0)
        row=run_task(task,1)
        self.assertTrue(row["success"],row)
        self.assertTrue(row["recovered"],row)
        self.assertGreaterEqual(row["steps"],2)

    def test_same_task_trial_is_deterministic(self):
        task=self.by_domain("office")
        a=run_task(task,1)
        b=run_task(task,2)
        self.assertEqual(a["success"],b["success"])
        self.assertEqual(a["terminal_code"],b["terminal_code"])
        # trial id is deliberately excluded from semantic comparison here.
        self.assertEqual(a["steps"],b["steps"])

if __name__=="__main__":
    unittest.main()