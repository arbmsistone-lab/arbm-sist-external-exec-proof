import unittest
from cloudflare_granite_capacity import granite_ratio_lane_tpd
from mesh_capacity import certify_mesh


class GraniteCapacityTests(unittest.TestCase):
    def test_conservative_lane_exceeds_needed_cloudflare_floor(self):
        row = granite_ratio_lane_tpd()
        self.assertEqual(row["certified_tokens_per_day"], 2341225)
        self.assertEqual(row["min_prompt_tokens"], 1024)
        self.assertEqual(row["max_output_ratio"], "0.2")

    def test_lightning_plus_granite_passes_three_million(self):
        cf = granite_ratio_lane_tpd()["certified_tokens_per_day"]
        routes = [
            {"name":"lightning","independence_pool":"lightning-account","account_verified":True,"recurring_free":True,"no_paid_fallback":True,"reset_verified":True,"certified_tokens_per_day":967741},
            {"name":"cloudflare-granite-ratio20","independence_pool":"cloudflare-account","account_verified":True,"recurring_free":True,"no_paid_fallback":True,"reset_verified":True,"certified_tokens_per_day":cf},
        ]
        out = certify_mesh(routes)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["certified_tokens_per_day"], 3308966)
        self.assertEqual(out["deficit_tokens_per_day"], 0)


if __name__ == "__main__":
    unittest.main()
