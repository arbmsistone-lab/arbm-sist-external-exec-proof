import unittest
from datetime import datetime,timedelta,timezone
from mesh_capacity import certify

class CapacityTests(unittest.TestCase):
    def sample(self,days=31):
        start=datetime(2026,1,1,tzinfo=timezone.utc)
        a={k:True for k in ("account_verified","recurring_free","payg_disabled","shared_usage_accounted","workspace_key_binding_verified","model_price_binding_verified","all_hard_limits_accounted","no_paid_fallback","throughput_sufficient")}
        a.update(tokens_per_month=100000000,included_credit_usd=10,input_price_per_million=.1,output_price_per_million=.1,other_hard_limit_tokens=100000000,actual_usage_tokens=0,other_usage_credit_usd=0,safety_reserve=1000000,cycle_start=start.isoformat(),cycle_end=(start+timedelta(days=days)).isoformat(),usage_observed_at=start.isoformat())
        return a,start
    def test_cycles_28_29_30_31(self):
        for days in (28,29,30,31):
            a,t=self.sample(days);r=certify(a,t);self.assertEqual(r["status"],"PASS");self.assertEqual(r["required_cycle_capacity"],days*3000000)
    def test_tpm_times_1440_is_not_allowance(self):
        self.assertNotEqual(certify({"tokens_per_minute":1300000})["status"],"PASS")
    def test_credit_price_alone_never_certifies(self):
        for cap in (None,1000000):
            a,t=self.sample();a["tokens_per_month"]=cap;self.assertNotEqual(certify(a,t)["status"],"PASS")
    def test_unknown_never_becomes_zero_real_capacity(self):
        a,t=self.sample();a["other_hard_limit_tokens"]=None;r=certify(a,t);self.assertIsNone(r["certified_monthly_capacity"])
    def test_shared_usage_and_payg(self):
        for key in ("shared_usage_accounted","payg_disabled","no_paid_fallback","workspace_key_binding_verified","recurring_free"):
            a,t=self.sample();a[key]=False;self.assertNotEqual(certify(a,t)["status"],"PASS")
    def test_exhaustion_and_reserve(self):
        a,t=self.sample();a["actual_usage_tokens"]=99000000;r=certify(a,t);self.assertEqual(r["safe_remaining_daily_budget"],0)
    def test_billing_reset_requires_new_evidence(self):
        a,t=self.sample();r=certify(a,t+timedelta(days=31));self.assertNotEqual(r["status"],"PASS")
    def test_stale_and_partial_day_usage(self):
        a,t=self.sample();now=t+timedelta(days=15,hours=1);a["usage_observed_at"]=now.isoformat();a["actual_usage_tokens"]=50000000;r=certify(a,now);self.assertEqual(r["remaining_days_in_cycle"],16);self.assertEqual(r["safe_remaining_daily_budget"],49000000//16)
        self.assertNotEqual(certify(a,now+timedelta(minutes=6))["status"],"PASS")
    def test_other_shared_credit_consumption(self):
        a,t=self.sample();a["other_usage_credit_usd"]=5;self.assertEqual(certify(a,t)["certified_monthly_capacity"],50000000)
if __name__=="__main__":unittest.main()
