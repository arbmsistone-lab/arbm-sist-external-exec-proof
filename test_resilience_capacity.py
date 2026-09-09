import json
import unittest
from resilience_capacity import certify_resilience


class ResilienceCapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open("account-capacity-evidence.json", encoding="utf-8") as f:
            cls.routes = json.load(f)["routes"]

    def test_current_3m_certificate_stays_green(self):
        r = certify_resilience(self.routes)
        self.assertEqual(r["base_3m_status"], "PASS")
        self.assertEqual(r["certified_tokens_per_day"], 3_308_966)

    def test_current_mesh_is_not_n_plus_one(self):
        r = certify_resilience(self.routes)
        self.assertEqual(r["n_plus_one_floor_tokens_per_day"], 967_741)
        self.assertEqual(r["n_plus_one_3m_status"], "FAIL_INSUFFICIENT_CAPACITY")

    def test_growth_gate_is_fail_closed(self):
        r = certify_resilience(self.routes)
        self.assertEqual(r["growth_5m_status"], "FAIL_INSUFFICIENT_CAPACITY")
        self.assertEqual(r["growth_5m_deficit_tokens_per_day"], 1_691_034)
