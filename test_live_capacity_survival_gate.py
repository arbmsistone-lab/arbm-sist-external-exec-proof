import unittest
from live_capacity_survival_gate import evaluate

E={'routes':[
 {'independence_pool':'groq-organization','certified_useful_units_per_day':2_000_000},
 {'independence_pool':'lightning-account','certified_useful_units_per_day':967_741},
 {'independence_pool':'cloudflare-account','certified_useful_units_per_day':5_546_032},
 {'independence_pool':'mistral-organization','certified_useful_units_per_day':2_304_000},
 {'independence_pool':'supabase-organization','certified_useful_units_per_day':2_100_000}]}
def row(p,ok=True):
 alias={'groq':'groq','lightning':'lightning-free','cloudflare':'cloudflare'}[p]
 return {'provider_hint':p,'http':200 if ok else 503,'mandatory_cost_usd':0,'paid_fallback_used':False,
         'provider_attempts':[{'route':alias,'status':200 if ok else 'quota_exhausted','parsed':ok}]}
PASS={'status':'PASS','http':200,'mandatory_cost_usd':0,'paid_fallback_used':False}

class LiveSurvivalTests(unittest.TestCase):
    def test_two_degraded_still_passes_above_5m(self):
        rows=[row('groq',False),row('lightning',False),row('cloudflare',True)]
        out=evaluate(E,rows,PASS,PASS)
        self.assertEqual(out['status'],'PASS')
        self.assertEqual(out['live_pools'],3)
        self.assertEqual(out['live_useful_units_per_day'],9_950_032)
    def test_below_floor_fails_closed(self):
        rows=[row('groq',False),row('lightning',False),row('cloudflare',False)]
        out=evaluate(E,rows,PASS,PASS)
        self.assertEqual(out['status'],'FAIL')
        self.assertLess(out['live_useful_units_per_day'],5_000_000)
    def test_paid_mistral_is_not_live(self):
        bad={**PASS,'paid_fallback_used':True}
        rows=[row('groq',True),row('lightning',True),row('cloudflare',False)]
        out=evaluate(E,rows,bad,PASS)
        self.assertFalse(out['provider_live']['mistral'])

if __name__=='__main__': unittest.main()
