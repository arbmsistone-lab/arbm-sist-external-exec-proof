import json, unittest
from merge_live_capacity_evidence import merge, qualified
from capacity_excellence import chaos_floors

class SevenOfSevenPromotionPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open('account-capacity-evidence.json',encoding='utf-8') as f:
            cls.base=json.load(f)

    def proof(self,name,pool,kind,useful,tokens=0):
        return {"provider":name,"independence_pool":pool,"capacity_kind":kind,
                "account_verified":True,"recurring_free":True,"reset_verified":True,
                "no_paid_fallback":True,"mandatory_cost_usd":0,"paid_fallback_used":False,
                "certified_useful_units_per_day":useful,"certified_tokens_per_day":tokens}

    def test_two_qualified_pools_reach_seven_and_keep_n2_above_5m(self):
        openrouter=self.proof('openrouter-liquid-free','openrouter-account-liquid-runtime','decisions',50)
        hf=self.proof('huggingface-novita-free','huggingface-account-novita-runtime','tokens',74441,74441)
        out=merge(self.base,[openrouter,hf],'synthetic-integration-test')
        pools={r.get('independence_pool') for r in out['routes'] if qualified({'provider':r.get('name'),'independence_pool':r.get('independence_pool'),'capacity_kind':r.get('capacity_kind','tokens'),'account_verified':r.get('account_verified'),'recurring_free':r.get('recurring_free'),'reset_verified':r.get('reset_verified'),'no_paid_fallback':r.get('no_paid_fallback'),'mandatory_cost_usd':r.get('mandatory_cost_usd',0),'paid_fallback_used':r.get('paid_fallback_used',False),'certified_useful_units_per_day':r.get('certified_useful_units_per_day'),'certified_tokens_per_day':r.get('certified_tokens_per_day')})}
        self.assertEqual(len(pools),7)
        self.assertEqual(out['certified_useful_units_per_day'],12992264)
        self.assertEqual(out['certified_tokens_per_day'],8588214)
        chaos=chaos_floors(out['routes'])
        self.assertEqual(chaos['n_plus_two_status'],'PASS')
        self.assertGreaterEqual(chaos['n_plus_two_floor_useful_units_per_day'],5_000_000)

    def test_incomplete_new_pool_is_not_promoted(self):
        bad=self.proof('bad','bad-pool','decisions',50)
        bad['account_verified']=False
        out=merge(self.base,[bad],'synthetic-integration-test')
        pools={r.get('independence_pool') for r in out['routes'] if qualified({'provider':r.get('name'),'independence_pool':r.get('independence_pool'),'capacity_kind':r.get('capacity_kind','tokens'),'account_verified':r.get('account_verified'),'recurring_free':r.get('recurring_free'),'reset_verified':r.get('reset_verified'),'no_paid_fallback':r.get('no_paid_fallback'),'mandatory_cost_usd':r.get('mandatory_cost_usd',0),'paid_fallback_used':r.get('paid_fallback_used',False),'certified_useful_units_per_day':r.get('certified_useful_units_per_day'),'certified_tokens_per_day':r.get('certified_tokens_per_day')})}
        self.assertEqual(len(pools),5)
        self.assertNotIn('bad-pool',pools)
        self.assertEqual(out['certified_useful_units_per_day'],12917773)

if __name__=='__main__': unittest.main()
