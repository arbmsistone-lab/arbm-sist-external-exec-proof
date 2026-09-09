import unittest
from mesh_capacity import certify_mesh
from capacity_excellence import chaos_floor

ZERO={"name":"zero","independence_pool":"zero-pool","account_verified":True,"recurring_free":True,"no_paid_fallback":True,"reset_verified":True,"certified_tokens_per_day":0}
LIVE={"name":"live","independence_pool":"live-pool","account_verified":True,"recurring_free":True,"no_paid_fallback":True,"reset_verified":True,"certified_tokens_per_day":3_000_000}

class ZeroCapacityPoolGateTests(unittest.TestCase):
    def test_zero_capacity_is_rejected_by_mesh(self):
        r=certify_mesh([ZERO,LIVE])
        self.assertEqual(r["independent_pools"],1)
        self.assertEqual(r["certified_tokens_per_day"],3_000_000)
        self.assertTrue(any(x["name"]=="zero" for x in r["rejected_routes"]))

    def test_zero_capacity_is_not_counted_by_chaos(self):
        r=chaos_floor([ZERO,LIVE],0)
        self.assertEqual(r["independent_pools"],1)
        self.assertEqual(r["surviving_tpd"],3_000_000)

if __name__=="__main__": unittest.main()
