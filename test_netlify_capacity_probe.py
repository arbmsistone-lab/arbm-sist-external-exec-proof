import io, json, os, unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import netlify_capacity_probe as n

class Resp:
    status=200
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def read(self): return json.dumps({"ok":True,"requested_model":n.MODEL}).encode()

class NetlifyProbeTests(unittest.TestCase):
    def test_conservative_formula(self):
        self.assertEqual(n.CERTIFIED_TPD,2_348_197)
        self.assertEqual(float(n.USABLE_USD),1.5)

    def test_missing_oidc_is_zero(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD"},clear=True), redirect_stdout(out): code=n.main()
        d=json.loads(out.getvalue()); self.assertEqual(code,0); self.assertEqual(d["certified_tokens_per_day"],0)

    def test_live_without_account_proof_is_zero(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD"},clear=True), patch.object(n,"oidc",return_value="jwt"), patch("urllib.request.urlopen",return_value=Resp()), patch.object(n,"account_proof",return_value=False), patch.object(n,"docs_proof",return_value=True), redirect_stdout(out): n.main()
        d=json.loads(out.getvalue()); self.assertEqual(d["status"],"LIVE_UNCERTIFIED"); self.assertEqual(d["certified_tokens_per_day"],0)
    def test_live_plus_account_and_docs_certifies(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD"},clear=True), patch.object(n,"oidc",return_value="jwt"), patch("urllib.request.urlopen",return_value=Resp()), patch.object(n,"account_proof",return_value=True), patch.object(n,"docs_proof",return_value=True), redirect_stdout(out): code=n.main()
        d=json.loads(out.getvalue()); self.assertEqual(code,0); self.assertEqual(d["status"],"PASS_ACCOUNT_BOUND"); self.assertEqual(d["certified_tokens_per_day"],2_348_197)
        self.assertTrue(d["recurring_free"]); self.assertTrue(d["reset_verified"]); self.assertTrue(d["no_paid_fallback"])

if __name__=="__main__": unittest.main()