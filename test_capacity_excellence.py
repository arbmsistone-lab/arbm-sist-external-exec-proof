import json, unittest
from datetime import datetime, timezone, timedelta
from capacity_excellence import evidence_fresh, monthly_governor, chaos_floor

class CapacityExcellenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open('account-capacity-evidence.json',encoding='utf-8') as f:
            cls.data=json.load(f)
        cls.routes=cls.data['routes']

    def test_evidence_ttl_fail_closed(self):
        now=datetime(2026,9,9,18,0,tzinfo=timezone.utc)
        self.assertTrue(evidence_fresh('2026-09-09T17:53:08Z',now))
        self.assertFalse(evidence_fresh('2026-09-08T17:53:08Z',now))
        self.assertFalse(evidence_fresh(None,now))

    def test_lightning_monthly_governor_preserves_reserve(self):
        r=monthly_governor(30_000_000,0,31,0.05)
        self.assertEqual(r['status'],'PASS')
        self.assertEqual(r['reserve_tokens'],1_500_000)
        self.assertEqual(r['daily_budget'],919_354)

    def test_current_n1_and_n2_fail_closed(self):
        self.assertEqual(chaos_floor(self.routes,1)['surviving_tpd'],2_967_741)
        self.assertEqual(chaos_floor(self.routes,1)['status'],'FAIL_INSUFFICIENT_CAPACITY')
        self.assertEqual(chaos_floor(self.routes,2)['surviving_tpd'],967_741)
        self.assertEqual(chaos_floor(self.routes,2)['status'],'FAIL_INSUFFICIENT_CAPACITY')

    def test_vikasit_closes_n1_but_not_n2(self):
        v={'name':'vikasit','independence_pool':'vikasit-account','account_verified':True,'recurring_free':True,'no_paid_fallback':True,'reset_verified':True,'certified_tokens_per_day':2_000_000}
        self.assertEqual(chaos_floor(self.routes+[v],1)['surviving_tpd'],4_967_741)
        self.assertEqual(chaos_floor(self.routes+[v],1)['status'],'PASS')
        self.assertEqual(chaos_floor(self.routes+[v],2)['status'],'FAIL_INSUFFICIENT_CAPACITY')

if __name__=='__main__': unittest.main()