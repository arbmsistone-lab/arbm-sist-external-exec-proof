import unittest
from datetime import datetime, timezone
from capacity_ceiling_gate import certify_ceiling

NOW=datetime(2026,9,9,18,45,tzinfo=timezone.utc)
EVID=[{"observed_at":"2026-09-09T18:00:00Z"}]

def r(name,pool,tpd):
    return {"name":name,"independence_pool":pool,"account_verified":True,
            "recurring_free":True,"no_paid_fallback":True,"reset_verified":True,
            "certified_tokens_per_day":tpd}

class CeilingGateTests(unittest.TestCase):
    def test_current_mesh_fails_ceiling_without_overclaim(self):
        routes=[r("cf","cf",4305723),r("l","l",967741),r("g","g",800000)]
        out=certify_ceiling(routes,EVID,NOW)
        self.assertEqual(out["status"],"FAIL")
        self.assertFalse(out["criteria"]["stretch_10m"])
        self.assertFalse(out["criteria"]["n_plus_one_3m"])
        self.assertFalse(out["criteria"]["n_plus_two_3m"])

    def test_true_ceiling_requires_10m_and_n2(self):
        routes=[r("a","a",4_000_000),r("b","b",3_500_000),r("c","c",3_200_000),r("d","d",3_000_000)]
        out=certify_ceiling(routes,EVID,NOW)
        self.assertEqual(out["status"],"PASS")
        self.assertTrue(all(out["criteria"].values()))

if __name__=='__main__': unittest.main()
