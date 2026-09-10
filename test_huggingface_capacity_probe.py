import io, json, os, unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import huggingface_capacity_probe as p

class HuggingFaceCapacityProbeTests(unittest.TestCase):
    def run_with_who(self, who):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD","HF_TOKEN":"x"},clear=True), \
             patch.object(p,"get_json",return_value=(200,who,{})), redirect_stdout(out):
            rc=p.main()
        return rc,json.loads(out.getvalue())

    def test_missing_token_is_zero(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD"},clear=True),redirect_stdout(out):
            rc=p.main()
        data=json.loads(out.getvalue())
        self.assertEqual(rc,0)
        self.assertEqual(data["status"],"NOT_CONFIGURED")
        self.assertEqual(data["certified_useful_units_per_day"],0)

    def test_canpay_null_is_not_proven(self):
        rc,data=self.run_with_who({"type":"user","isPro":False,"canPay":None})
        self.assertEqual(rc,0)
        self.assertEqual(data["status"],"ACCOUNT_BILLING_NOT_PROVEN_FREE")
        self.assertEqual(data["certified_useful_units_per_day"],0)

    def test_canpay_true_is_rejected(self):
        rc,data=self.run_with_who({"type":"user","isPro":False,"canPay":True})
        self.assertEqual(rc,0)
        self.assertEqual(data["status"],"ACCOUNT_BILLING_NOT_PROVEN_FREE")
        self.assertEqual(data["certified_tokens_per_day"],0)

    def test_free_account_requires_live_inference(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD","HF_TOKEN":"x"},clear=True), \
             patch.object(p,"get_json",return_value=(200,{"type":"user","isPro":False,"canPay":False},{})), \
             patch.object(p,"live_call",return_value=(False,403,{})), redirect_stdout(out):
            rc=p.main()
        data=json.loads(out.getvalue())
        self.assertEqual(rc,0)
        self.assertEqual(data["status"],"LIVE_UNCERTIFIED")
        self.assertEqual(data["certified_useful_units_per_day"],0)

if __name__=='__main__': unittest.main()
