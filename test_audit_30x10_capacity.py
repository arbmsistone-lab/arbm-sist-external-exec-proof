import unittest
from datetime import datetime, timezone
from audit_30x10_capacity import audit

NOW=datetime(2026,9,9,18,40,tzinfo=timezone.utc)

def route(name,pool,tpd):
    return {"name":name,"independence_pool":pool,"account_verified":True,
            "recurring_free":True,"no_paid_fallback":True,"reset_verified":True,
            "certified_tokens_per_day":tpd}

class AuditTests(unittest.TestCase):
    def test_current_like_mesh_fails_n1_and_n2(self):
        routes=[route("cf","cf",4305723),route("lightning","l",967741),route("groq","g",32259)]
        r=audit(routes,[{"observed_at":"2026-09-09T18:00:00Z"}],NOW)
        self.assertEqual(r["checks"],300)
        self.assertEqual(r["status"],"FAIL")
        self.assertIn("n_plus_one",r["findings"])
        self.assertIn("n_plus_two",r["findings"])

    def test_top_tier_mesh_passes_300_checks(self):
        routes=[route("a","a",4_000_000),route("b","b",3_500_000),route("c","c",3_200_000),route("d","d",3_000_000)]
        r=audit(routes,[{"observed_at":"2026-09-09T18:00:00Z"}],NOW)
        self.assertEqual(r["status"],"PASS")
        self.assertEqual(r["passed_checks"],300)

if __name__=='__main__': unittest.main()
