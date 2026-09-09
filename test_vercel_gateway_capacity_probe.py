import io, json, os, unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import vercel_gateway_capacity_probe as v

class VercelGatewayProbeTests(unittest.TestCase):
    def run_probe(self, quota=(True,2,5,"api_key_id_key1"), account=True, docs=True, live=(True,200), env=None):
        out=io.StringIO(); e={"ZERO_SPEND_MODE":"HARD","VERCEL_AI_GATEWAY_API_KEY":"dummy","VERCEL_AI_GATEWAY_API_KEY_ID":"key1"}; e.update(env or {})
        with patch.dict(os.environ,e,clear=True), patch.object(v,"quota_proof",return_value=quota), patch.object(v,"account_proof",return_value=account), patch.object(v,"docs_proof",return_value=docs), patch.object(v,"live_call",return_value=live), redirect_stdout(out):
            code=v.main()
        return code,json.loads(out.getvalue())

    def test_two_dollar_budget_capacity(self):
        self.assertEqual(v.capacity_for_budget(2),2_000_000)

    def test_missing_key_or_id_is_zero(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD","VERCEL_AI_GATEWAY_API_KEY":"dummy"},clear=True), redirect_stdout(out): code=v.main()
        d=json.loads(out.getvalue()); self.assertEqual(code,0); self.assertEqual(d["certified_tokens_per_day"],0)

    def test_quota_below_two_is_zero(self):
        _,d=self.run_probe(quota=(False,1,5,"api_key_id_key1"))
        self.assertEqual(d["status"],"LIVE_UNCERTIFIED"); self.assertEqual(d["certified_tokens_per_day"],0)

    def test_insufficient_balance_is_zero(self):
        _,d=self.run_probe(quota=(False,2,1,"api_key_id_key1"))
        self.assertEqual(d["certified_tokens_per_day"],0)

    def test_live_monthly_two_dollar_quota_certifies_two_million(self):
        code,d=self.run_probe()
        self.assertEqual(code,0); self.assertEqual(d["status"],"PASS_ACCOUNT_BOUND")
        self.assertEqual(d["certified_tokens_per_day"],2_000_000)
        self.assertEqual(d["key_budget_usd"],2.0); self.assertEqual(d["credit_balance_usd"],5.0)
        self.assertTrue(d["recurring_free"]); self.assertTrue(d["reset_verified"]); self.assertTrue(d["no_paid_fallback"])

if __name__=="__main__": unittest.main()
