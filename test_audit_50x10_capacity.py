import unittest
from datetime import datetime,timezone
from audit_50x10_capacity import audit
NOW=datetime(2026,9,9,20,0,tzinfo=timezone.utc); E=[{'observed_at':'2026-09-09T19:30:00Z'}]
def route(n,p,t): return {'name':n,'independence_pool':p,'account_verified':True,'recurring_free':True,'reset_verified':True,'no_paid_fallback':True,'paid_fallback_used':False,'mandatory_cost_usd':0,'certified_useful_units_per_day':t,'evidence':['live-proof']}
class T(unittest.TestCase):
 def test_current_is_discriminated_fail(self):
  x=audit([route('cf','cf',5546032),route('l','l',967741),route('g','g',800000)],E,NOW); self.assertEqual(x['checks'],500); self.assertEqual(x['status'],'FAIL'); self.assertGreater(x['passed_checks'],0); self.assertLess(x['passed_checks'],500); self.assertIn('n_plus_one_3m',x['findings']); self.assertIn('stretch_10m',x['findings'])
 def test_true_ceiling_500(self):
  x=audit([route('a','a',4000000),route('b','b',3500000),route('c','c',3200000),route('d','d',3000000)],E,NOW); self.assertEqual(x['status'],'PASS'); self.assertEqual(x['passed_checks'],500)
 def test_trial_rejected(self):
  rs=[route('a','a',4000000),route('b','b',3500000),route('c','c',3200000),route('d','d',3000000)]; rs[3]['temporary_trial']=True; x=audit(rs,E,NOW); self.assertIn('no_temporary_trial',x['findings'])
if __name__=='__main__': unittest.main()