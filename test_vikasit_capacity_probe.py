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

    def test_model_and_endpoint_are_hardcoded(self):
        self.assertEqual(v.MODEL, "vikasit-nova")
        self.assertEqual(v.ENDPOINT, "https://api.vikasit.ai/v1/chat/completions")
        self.assertEqual(v.DOCUMENTED_TPD, 2_000_000)
