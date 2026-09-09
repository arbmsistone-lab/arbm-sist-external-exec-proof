import unittest
from distributed_capacity import qualify_user_pays

class DistributedCapacityTests(unittest.TestCase):
    def test_shared_puter_token_is_rejected(self):
        r = qualify_user_pays({
            "documented_user_pays": True,
            "developer_cost_zero": True,
            "per_user_isolation": False,
            "request_scoped_auth": False,
            "shared_developer_credential": True,
        })
        self.assertFalse(r["qualified"])
        self.assertIn("per_user_isolation", r["failed"])
        self.assertEqual(r["central_certified_tokens_per_day"], 0)

    def test_request_scoped_user_pays_is_qualified(self):
        r = qualify_user_pays({
            "documented_user_pays": True,
            "developer_cost_zero": True,
            "per_user_isolation": True,
            "request_scoped_auth": True,
            "shared_developer_credential": False,
        })
        self.assertTrue(r["qualified"])
        self.assertEqual(r["mode"], "USER_PAYS_DISTRIBUTED")
        self.assertEqual(r["developer_marginal_ai_cost"], 0)
        self.assertEqual(r["central_certified_tokens_per_day"], 0)

if __name__ == "__main__":
    unittest.main()
