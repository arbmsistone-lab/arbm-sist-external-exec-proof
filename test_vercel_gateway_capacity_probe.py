import io, json, os, unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import vercel_gateway_capacity_probe as v

class Resp:
    status=200
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self): return b'{"choices":[{"message":{"content":"ARBM_VERCEL_PASS"}}]}'

class VercelGatewayProbeTests(unittest.TestCase):
    def test_formula_is_exactly_five_million(self):
        self.assertEqual(v.CERTIFIED_TPD,5_000_000)

    def test_missing_key_is_zero(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD"},clear=True), redirect_stdout(out): code=v.main()
        data=json.loads(out.getvalue()); self.assertEqual(code,0); self.assertEqual(data["certified_tokens_per_day"],0)

    def test_live_without_account_or_docs_stays_zero(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD","VERCEL_AI_GATEWAY_API_KEY":"dummy"},clear=True), patch("urllib.request.urlopen",return_value=Resp()), patch.object(v,"account_proof",return_value=False), patch.object(v,"docs_proof",return_value=True), redirect_stdout(out): code=v.main()
        data=json.loads(out.getvalue()); self.assertEqual(code,0); self.assertEqual(data["status"],"LIVE_UNCERTIFIED"); self.assertEqual(data["certified_tokens_per_day"],0)
    def test_live_plus_hobby_and_docs_certifies_five_million(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD","VERCEL_AI_GATEWAY_API_KEY":"dummy"},clear=True), patch("urllib.request.urlopen",return_value=Resp()), patch.object(v,"account_proof",return_value=True), patch.object(v,"docs_proof",return_value=True), redirect_stdout(out): code=v.main()
        data=json.loads(out.getvalue()); self.assertEqual(code,0); self.assertEqual(data["status"],"PASS_ACCOUNT_BOUND"); self.assertEqual(data["certified_tokens_per_day"],5_000_000)
        self.assertTrue(data["recurring_free"]); self.assertTrue(data["reset_verified"]); self.assertTrue(data["no_paid_fallback"])

if __name__=="__main__": unittest.main()