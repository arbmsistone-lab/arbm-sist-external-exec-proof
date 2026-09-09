import io, json, os, unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import openrouter_capacity_probe as p

class OpenRouterCapacityProbeTests(unittest.TestCase):
    def test_contract_is_conservative_requests_not_invented_tokens(self):
        self.assertEqual(p.CERTIFIED_REQUESTS_PER_DAY,50)
        self.assertEqual(p.CAPACITY_KIND,"decisions")
        self.assertEqual(p.MODEL,"openrouter/free")

    def test_missing_key_is_zero(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD"},clear=True),redirect_stdout(out):
            rc=p.main()
        data=json.loads(out.getvalue())
        self.assertEqual(rc,0)
        self.assertEqual(data["status"],"NOT_CONFIGURED")
        self.assertEqual(data["certified_useful_units_per_day"],0)
        self.assertEqual(data["certified_tokens_per_day"],0)

if __name__=='__main__': unittest.main()
