import unittest
from arbm_core.benchmark_program import (
    BenchmarkSource, build_internal_catalog, import_external_catalog,
    run_trials, summarize, promotion_gate,
)

class CatalogTests(unittest.TestCase):
    def test_internal_catalog_is_exactly_400_balanced_and_not_frontier_comparable(self):
        tasks=build_internal_catalog(400)
        self.assertEqual(len(tasks),400)
        domains={}
        for task in tasks:
            domains[task.domain]=domains.get(task.domain,0)+1
            self.assertEqual(task.source,BenchmarkSource.INTERNAL)
            self.assertFalse(task.metadata["frontier_comparable"])
        self.assertEqual(set(domains.values()),{50})
        self.assertEqual(len({t.digest for t in tasks}),400)

    def test_external_catalog_requires_identity(self):
        with self.assertRaises(ValueError):
            import_external_catalog([{"domain":"gui","objective":"x"}],benchmark="osworld")

    def test_external_catalog_is_separate(self):
        tasks=import_external_catalog([
            {"task_id":"001","domain":"gui","instruction":"Do a task","difficulty":3}
        ],benchmark="osworld-verified")
        self.assertEqual(tasks[0].source,BenchmarkSource.EXTERNAL)
        self.assertTrue(tasks[0].metadata["frontier_comparable"])

class MetricsTests(unittest.TestCase):
    def test_internal_perfect_run_is_internal_only(self):
        tasks=build_internal_catalog(8)
        results=run_trials(tasks,lambda task,trial:{
            "success":True,"recovered":False,"steps":3,"cost_usd":0.0,
            "terminal_code":"PASS","trace":{"task":task.task_id,"stable":True}
        },repetitions=3)
        metrics=summarize(tasks,results)
        gate=promotion_gate(metrics)
        self.assertTrue(gate.passed)
        self.assertEqual(gate.level,"INTERNAL_ELITE_CANDIDATE")
        self.assertNotEqual(gate.level,"FRONTIER_CANDIDATE")

    def test_nondeterminism_blocks_promotion(self):
        tasks=build_internal_catalog(8)
        results=run_trials(tasks,lambda task,trial:{
            "success":True,"steps":1,"cost_usd":0,
            "terminal_code":"PASS",
            "trace":{"trial":trial},
        },repetitions=3)
        metrics=summarize(tasks,results)
        gate=promotion_gate(metrics)
        self.assertFalse(gate.passed)
        self.assertTrue(any(x.startswith("DETERMINISM_BELOW_99") for x in gate.reasons))

    def test_external_frontier_gate_requires_300_tasks_and_80_percent(self):
        rows=[{"task_id":f"{i:03d}","domain":"gui","instruction":"external"} for i in range(300)]
        tasks=import_external_catalog(rows,benchmark="osworld-verified")
        results=run_trials(tasks,lambda task,trial:{
            "success": int(task.metadata["external_task_id"]) % 5 != 0,
            "steps":5,"cost_usd":0,"terminal_code":"PASS" if int(task.metadata["external_task_id"])%5!=0 else "FAIL",
            "trace":{"task":task.task_id,"ok":int(task.metadata["external_task_id"])%5!=0}
        },repetitions=2)
        metrics=summarize(tasks,results)
        self.assertAlmostEqual(metrics.success_rate,0.80)
        gate=promotion_gate(metrics)
        self.assertTrue(gate.passed)
        self.assertEqual(gate.level,"FRONTIER_CANDIDATE")

if __name__=="__main__":
    unittest.main()