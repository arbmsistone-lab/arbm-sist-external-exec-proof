import unittest
from merge_live_capacity_evidence import merge

BASE={"target_tokens_per_day":3_000_000,"routes":[{"name":"base","independence_pool":"base-pool","account_verified":True,"recurring_free":True,"reset_verified":True,"no_paid_fallback":True,"certified_tokens_per_day":3_000_000}]}

def proof(pool="new-pool",cap=2_000_000,**kw):
    p={"provider":"new","independence_pool":pool,"account_verified":True,"recurring_free":True,"reset_verified":True,"no_paid_fallback":True,"mandatory_cost_usd":0,"paid_fallback_used":False,"certified_tokens_per_day":cap}
    p.update(kw); return p

class MergeEvidenceTests(unittest.TestCase):
    def test_qualified_new_pool_is_added(self):
        r=merge(BASE,[proof()],"123")
        self.assertEqual(r["certified_tokens_per_day"],5_000_000)
        self.assertEqual(len(r["routes"]),2)

    def test_paid_or_incomplete_proof_is_rejected(self):
        bad1=proof(paid_fallback_used=True)
        bad2=proof(reset_verified=False)
        r=merge(BASE,[bad1,bad2],"123")
        self.assertEqual(r["certified_tokens_per_day"],3_000_000)
        self.assertEqual(len(r["routes"]),1)

    def test_same_pool_uses_max_not_sum(self):
        r=merge(BASE,[proof("base-pool",2_000_000)],"123")
        self.assertEqual(r["certified_tokens_per_day"],3_000_000)
        r=merge(BASE,[proof("base-pool",4_000_000)],"123")
        self.assertEqual(r["certified_tokens_per_day"],4_000_000)
        self.assertEqual(len(r["routes"]),1)

if __name__=="__main__": unittest.main()
