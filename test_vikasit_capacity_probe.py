import os
import unittest
from unittest.mock import patch
import vikasit_capacity_probe as v


class VikasitProbeTests(unittest.TestCase):
    def test_missing_key_is_zero_capacity(self):
        with patch.dict(os.environ, {}, clear=True):
            r = v.probe()
        self.assertEqual(r["status"], "NOT_CONFIGURED")
        self.assertEqual(r["certified_tokens_per_day"], 0)
        self.assertEqual(r["documented_free_tokens_per_day"], 0)

    def test_stale_two_million_claim_is_removed(self):
        self.assertEqual(v.MODEL, "vikasit-nova")
        self.assertEqual(v.ENDPOINT, "https://api.vikasit.ai/v1/chat/completions")
        self.assertEqual(v.DOCUMENTED_TPD, 0)

    def test_live_without_current_official_tpd_proof_stays_uncertified(self):
        class Resp:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self): return b'{"model":"vikasit-nova","choices":[{"message":{"content":"PASS"}}]}'
        with patch.dict(os.environ, {"VIKASIT_API_KEY":"dummy","VIKASIT_RESET_WINDOW_VERIFIED":"1"}, clear=True), patch("urllib.request.urlopen", return_value=Resp()):
            r = v.probe()
        self.assertEqual(r["status"], "LIVE_UNCERTIFIED")
        self.assertFalse(r["official_tpd_verified"])
        self.assertEqual(r["certified_tokens_per_day"], 0)
