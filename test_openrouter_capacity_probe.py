import io, json, os, unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import openrouter_capacity_probe as p

class OpenRouterCapacityProbeTests(unittest.TestCase):
    def test_contract_is_exact_two_million(self):
        self.assertEqual(p.MIN_REQUESTS_PER_DAY,50)
        self.assertEqual(p.MIN_USEFUL_INPUT_TOKENS,40_000)
        self.assertEqual(p.CERTIFIED_TPD,2_000_000)
        self.assertEqual(p.MODEL,"openrouter/free")

    def test_missing_key_is_zero(self):
        env={"ZERO_SPEND_MODE":"HARD"}
        out=io.StringIO()
        with patch.dict(os.environ,env,clear=True), redirect_stdout(out):
            rc=p.main()
        data=json.loads(out.getvalue())
        self.assertEqual(rc,0)
        self.assertEqual(data["status"],"NOT_CONFIGURED")
        self.assertEqual(data["certified_tokens_per_day"],0)
