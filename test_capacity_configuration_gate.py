import json, os, tempfile, unittest
from unittest.mock import patch
import capacity_configuration_gate as g

class GateTests(unittest.TestCase):
    def run_gate(self, live, env=None):
        with tempfile.NamedTemporaryFile('w',delete=False,encoding='utf-8',suffix='.json') as f:
            json.dump({'live':live},f); path=f.name
        try:
            with patch.dict(os.environ, env or {}, clear=True): return g.check(path)
        finally: os.unlink(path)
    def test_openrouter_claim_requires_current_key(self):
        e=self.run_gate({'openrouter':{'connected':True,'certified_tokens_per_day':0}})
        self.assertIn('OPENROUTER_CLAIM_WITHOUT_CURRENT_CREDENTIAL',e)
    def test_openrouter_zero_claim_without_key_passes(self):
        e=self.run_gate({'openrouter':{'connected':False,'live_qualified':False,'account_specific':False,'certified_tokens_per_day':0,'daily_capacity_counted_for_gate':0}})
        self.assertEqual(e,[])
    def test_mistral_count_requires_admin_free_proof(self):
        e=self.run_gate({'mistral':{'daily_capacity_counted_for_gate':1,'live_proven':True,'free_mode_admin_proven':False,'payg_disabled_proven':False}})
        self.assertIn('MISTRAL_COUNTED_WITHOUT_FREE_MODE_PROOF',e)
        self.assertIn('MISTRAL_COUNTED_WITHOUT_PAYG_DISABLED_PROOF',e)

if __name__=='__main__': unittest.main()
