import io, json, os, unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import sambanova_capacity_probe as s

def row(model, ok):
    return {"model":model,"http":200,"live":True,"account_bound":ok,"headers":{"x-ratelimit-limit-tokens-day":"200000"} if ok else {}}

def run_rows(rows):
    out=io.StringIO()
    with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD","SAMBANOVA_API_KEY":"dummy"},clear=True), patch.object(s,"call",side_effect=rows), redirect_stdout(out):
        code=s.main()
    return code,json.loads(out.getvalue())

class SambaNovaProbeTests(unittest.TestCase):
    def test_missing_key_is_zero(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD"},clear=True), redirect_stdout(out): code=s.main()
        data=json.loads(out.getvalue()); self.assertEqual(code,0); self.assertEqual(data["certified_tokens_per_day"],0)

    def test_one_proven_model_only_certifies_200k(self):
        code,data=run_rows([row(s.MODELS[0],True),row(s.MODELS[1],False)])
        self.assertEqual(code,0); self.assertEqual(data["status"],"PARTIAL_ACCOUNT_BOUND"); self.assertEqual(data["certified_tokens_per_day"],200_000)

    def test_two_distinct_proven_models_certify_400k(self):
        code,data=run_rows([row(s.MODELS[0],True),row(s.MODELS[1],True)])
        self.assertEqual(code,0); self.assertEqual(data["status"],"PASS_ACCOUNT_BOUND"); self.assertEqual(data["certified_tokens_per_day"],400_000)
        self.assertEqual(data["independence_pool"],"sambanova-account")

if __name__=="__main__": unittest.main()
