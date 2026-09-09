import unittest
import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("adaptive-router-quota-shield-sim.py")
spec = importlib.util.spec_from_file_location("sim", MODULE_PATH)
sim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim)

class RouterQuotaShieldTests(unittest.TestCase):
    def setUp(self):
        self.routes = sim.demo_routes()

    def test_hard_filter_blocks_unknown_cost(self):
        unknown = next(r for r in self.routes if r.name == "unknown-cloud")
        self.assertFalse(sim.hard_filter(unknown))

    def test_hard_filter_blocks_heavy_local(self):
        local = next(r for r in self.routes if r.name == "local-heavy")
        self.assertFalse(sim.hard_filter(local))

    def test_normal_route_prefers_best_free_remote(self):
        selected = sim.choose_route(self.routes, 20000, 10000)
        self.assertEqual(selected.name, "github-free")

    def test_provider_failure_fails_over(self):
        result = sim.simulate_failover(self.routes, "github", 20000, 10000)
        self.assertEqual(result["selected_provider"], "gitlab")
        self.assertTrue(result["zero_spend"])
        self.assertFalse(result["heavy_local"])

    def test_quota_shield_blocks_insufficient_capacity(self):
        starved = [
            sim.replace(r, remaining_tokens=25000)
            if r.name in {"github-free", "gitlab-free"} else r
            for r in self.routes
        ]
        self.assertIsNone(sim.choose_route(starved, 20000, 10000))

    def test_open_circuit_is_excluded(self):
        routes = [
            sim.replace(r, circuit_open=True)
            if r.name == "github-free" else r
            for r in self.routes
        ]
        selected = sim.choose_route(routes, 20000, 10000)
        self.assertEqual(selected.name, "gitlab-free")

if __name__ == "__main__":
    unittest.main()
