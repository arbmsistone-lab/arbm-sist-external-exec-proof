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
        self.assertEqual(r["certified_tokens_per_day"], 7_313_773)

    def test_current_mesh_is_not_n_plus_one(self):
        r = certify_resilience(self.routes)
        self.assertEqual(r["n_plus_one_floor_tokens_per_day"], 1_767_741)
        self.assertEqual(r["n_plus_one_3m_status"], "FAIL_INSUFFICIENT_CAPACITY")

    def test_growth_gate_passes_with_concise_cloudflare_lane(self):
        r = certify_resilience(self.routes)
        self.assertEqual(r["growth_5m_status"], "PASS")
        self.assertEqual(r["growth_5m_deficit_tokens_per_day"], 0)

    def test_vikasit_two_million_closes_n_plus_one_exactly(self):
        vikasit = {"name":"vikasit-nova-free","independence_pool":"vikasit-account","account_verified":True,"recurring_free":True,"no_paid_fallback":True,"reset_verified":True,"certified_tokens_per_day":2_000_000}
        r = certify_resilience(self.routes + [vikasit])
        self.assertEqual(r["independent_pools"], 4)
        self.assertEqual(r["n_plus_one_floor_tokens_per_day"], 3_767_741)
        self.assertEqual(r["n_plus_one_3m_status"], "PASS")
