import unittest
from datetime import datetime, timezone, timedelta
from adaptive_capacity_router import eligible, choose, failover_chain, simulate_failover

BASE={"account_verified":True,"recurring_free":True,"reset_verified":True,"no_paid_fallback":True,
      "mandatory_cost_usd":0,"paid_fallback_used":False,"healthy":True,"capacity_kind":"decisions"}

def r(name,pool,cap,**extra):
    x={**BASE,"name":name,"independence_pool":pool,"certified_useful_units_per_day":cap}
    x.update(extra); return x

class RouterTests(unittest.TestCase):
    def test_highest_healthy_remaining_wins(self):
        rows=[r("a","a",100),r("b","b",200)]
        self.assertEqual(choose(rows)["name"],"b")
    def test_paid_or_exhausted_never_routes(self):
        rows=[r("paid","p",999,mandatory_cost_usd=1),r("empty","e",999,quota_exhausted=True),r("ok","o",1)]
        self.assertEqual(choose(rows)["name"],"ok")
    def test_cooldown_is_skipped(self):
        now=datetime.now(timezone.utc)
        rows=[r("cool","c",999,cooldown_until=(now+timedelta(minutes=5)).isoformat()),r("ok","o",1)]
        self.assertEqual(choose(rows,now)["name"],"ok")
    def test_two_pool_loss_still_has_chain(self):
        rows=[r("a","a",5_000_000),r("b","b",2_000_000),r("c","c",1_000_000)]
        out=simulate_failover(rows,{"a","b"})
        self.assertEqual(out["status"],"PASS")
        self.assertEqual(out["selected"]["name"],"c")
    def test_no_eligible_route_fails_closed(self):
        out=simulate_failover([r("x","x",1,healthy=False)])
        self.assertEqual(out["status"],"FAIL_NO_FREE_CAPACITY")
        self.assertIsNone(out["selected"])
    def test_chain_has_unique_independent_pools(self):
        rows=[r("a1","a",100),r("a2","a",90),r("b","b",80)]
        chain=failover_chain(rows)
        pools=[]
        for row in chain:
            if row["independence_pool"] not in pools: pools.append(row["independence_pool"])
        self.assertEqual(set(pools),{"a","b"})

if __name__=="__main__": unittest.main()
