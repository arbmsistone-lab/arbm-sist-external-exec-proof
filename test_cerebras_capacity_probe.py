import io, json, os, unittest
from unittest.mock import patch
import cerebras_capacity_probe as c

class CerebrasCapacityProbeTests(unittest.TestCase):
    def test_missing_key_stays_zero(self):
        with patch.dict(os.environ, {"ZERO_SPEND_MODE":"HARD"}, clear=True), \
             patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(c.main(), 0)
        row=json.loads(out.getvalue())
        self.assertEqual(row["status"], "NOT_CONFIGURED")
        self.assertEqual(row["certified_tokens_per_day"], 0)

    def test_two_free_model_buckets_can_certify_two_million(self):
        rows=[
            {"model":"gpt-oss-120b","valid":True,"certified_tokens_per_day":1_000_000},
            {"model":"zai-glm-4.7","valid":True,"certified_tokens_per_day":1_000_000},
        ]
        with patch.dict(os.environ, {"ZERO_SPEND_MODE":"HARD","CEREBRAS_API_KEY":"dummy"}, clear=True), \
             patch.object(c,"probe_model",side_effect=rows), \
             patch("sys.stdout",new_callable=io.StringIO) as out:
            self.assertEqual(c.main(),0)
        row=json.loads(out.getvalue())
        self.assertEqual(row["status"],"PASS")
        self.assertEqual(row["certified_tokens_per_day"],2_000_000)

    def test_partial_or_unproven_bucket_fails_closed(self):
        rows=[
            {"model":"gpt-oss-120b","valid":True,"certified_tokens_per_day":1_000_000},
            {"model":"zai-glm-4.7","valid":False,"certified_tokens_per_day":0},
        ]
        with patch.dict(os.environ, {"ZERO_SPEND_MODE":"HARD","CEREBRAS_API_KEY":"dummy"}, clear=True), \
             patch.object(c,"probe_model",side_effect=rows), \
             patch("sys.stdout",new_callable=io.StringIO) as out:
            self.assertEqual(c.main(),0)
        row=json.loads(out.getvalue())
        self.assertEqual(row["status"],"LIVE_UNCERTIFIED")
        self.assertEqual(row["certified_tokens_per_day"],0)

if __name__ == "__main__":
    unittest.main()
