import unittest
from cloudflare_granite_capacity import granite_concise_lane_tpd, granite_concise32_lane_tpd, granite_ratio_lane_tpd
from mesh_capacity import certify_mesh


class GraniteCapacityTests(unittest.TestCase):
    def test_conservative_lane_exceeds_needed_cloudflare_floor(self):
        row = granite_ratio_lane_tpd()
        self.assertEqual(row["certified_tokens_per_day"], 2341225)
        self.assertEqual(row["min_prompt_tokens"], 1024)
        self.assertEqual(row["max_output_ratio"], "0.2")

    def test_concise_lane_exceeds_five_million_with_lightning(self):
        row = granite_concise_lane_tpd()
        self.assertEqual(row["certified_tokens_per_day"], 4305723)
        self.assertEqual(row["min_prompt_tokens"], 1024)
        self.assertEqual(row["max_output_tokens"], 102)

    def test_concise32_lane_is_live_promotable_floor(self):
        row = granite_concise32_lane_tpd()
        self.assertEqual(row["certified_tokens_per_day"], 5546032)
        self.assertEqual(row["min_prompt_tokens"], 1024)
        self.assertEqual(row["max_output_tokens"], 32)
    def test_lightning_plus_granite_passes_five_million(self):
        cf = granite_concise_lane_tpd()["certified_tokens_per_day"]
        routes = [
            {"name":"lightning","independence_pool":"lightning-account","account_verified":True,"recurring_free":True,"no_paid_fallback":True,"reset_verified":True,"certified_tokens_per_day":967741},
            {"name":"cloudflare-granite-concise10","independence_pool":"cloudflare-account","account_verified":True,"recurring_free":True,"no_paid_fallback":True,"reset_verified":True,"certified_tokens_per_day":cf},
        ]
        out = certify_mesh(routes)
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["certified_tokens_per_day"], 5273464)
        self.assertEqual(out["deficit_tokens_per_day"], 0)


if __name__ == "__main__":
    unittest.main()
