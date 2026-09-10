import io, json, os, unittest
from contextlib import redirect_stdout
from unittest.mock import patch
import openrouter_capacity_probe as p

class OpenRouterCapacityProbeTests(unittest.TestCase):
    def test_contract_is_conservative_and_pinned(self):
        self.assertEqual(p.CERTIFIED_REQUESTS_PER_DAY, 50)
        self.assertEqual(p.MODEL, "liquid/lfm-2.5-2.6b:free")
        self.assertEqual(p.EXPECTED_PROVIDER, "liquid")

    def test_missing_key_is_zero(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD"},clear=True),redirect_stdout(out):
            rc=p.main()
        data=json.loads(out.getvalue())
        self.assertEqual(rc,0)
        self.assertEqual(data["status"],"NOT_CONFIGURED")
        self.assertEqual(data["certified_useful_units_per_day"],0)
        self.assertEqual(data["certified_tokens_per_day"],0)

    def test_selected_provider_requires_exact_single_match(self):
        self.assertEqual(p.selected_provider({"openrouter_metadata":{"endpoints":{"available":[{"provider":"liquid","selected":True}]}}}),"liquid")
        self.assertIsNone(p.selected_provider({"openrouter_metadata":{"endpoints":{"available":[{"provider":"other","selected":True},{"provider":"liquid","selected":True}]}}}))

    def test_non_free_account_is_rejected(self):
        out=io.StringIO()
        with patch.dict(os.environ,{"ZERO_SPEND_MODE":"HARD","OPENROUTER_API_KEY":"x"},clear=True), \
             patch.object(p,"call",return_value=(200,{"data":{"is_free_tier":False}})), redirect_stdout(out):
            rc=p.main()
        data=json.loads(out.getvalue())
        self.assertEqual(rc,2)
        self.assertEqual(data["status"],"ACCOUNT_NOT_PROVEN_FREE")
        self.assertEqual(data["certified_useful_units_per_day"],0)

if __name__=='__main__': unittest.main()
