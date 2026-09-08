import copy
import unittest
from arbm_provider_probe import live_proven, model_unavailable

class ProofTests(unittest.TestCase):
    def setUp(self):
        self.data = {"ok": True, "status": "PASS", "provider": "mistral-free",
                     "mandatory_cost_usd": 0, "paid_fallback_used": False,
                     "provider_attempts": [{"route": "mistral-free", "status": 200, "parsed": True, "mandatory_cost_usd": 0, "paid_fallback_used": False}]}
    def test_real_success(self):
        self.assertTrue(live_proven(200, self.data))
    def test_failures_never_promote(self):
        for status in (401, 403, 429, 503, None):
            self.assertFalse(live_proven(status, self.data))
        for key, value in (("ok", False), ("status", "WAITING_FREE_CAPACITY"),
                           ("provider", "paid"), ("mandatory_cost_usd", 1),
                           ("mandatory_cost_usd", False), ("paid_fallback_used", True)):
            data = copy.deepcopy(self.data); data[key] = value
            self.assertFalse(live_proven(200, data))
        for status in (401, 403, 429, 503, "transport"):
            data = copy.deepcopy(self.data); data["provider_attempts"][0]["status"] = status
            self.assertFalse(live_proven(200, data))
    def test_missing_attempt_cost_evidence_never_promotes(self):
        for key in ("mandatory_cost_usd", "paid_fallback_used", "parsed"):
            data = copy.deepcopy(self.data)
            del data["provider_attempts"][0][key]
            self.assertFalse(live_proven(200, data))
    def test_paid_or_unknown_mesh_attempt_never_promotes(self):
        for attempt in ({"route": "paid"}, {"route": "google", "paid_fallback_used": True}):
            data = copy.deepcopy(self.data)
            data["provider_attempts"].append(attempt)
            self.assertFalse(live_proven(200, data, mesh=True))
    def test_only_model_unavailability_retries(self):
        for status in (400, 404, 422):
            self.assertTrue(model_unavailable({"provider_attempts": [
                {"route": "mistral-free", "status": status, "error_message": "model not found"}]}))
        for status in (401, 403, 429, 503, "transport"):
            self.assertFalse(model_unavailable({"provider_attempts": [
                {"route": "mistral-free", "status": status, "error_message": "model not found"}]}))
        self.assertFalse(model_unavailable({"provider_attempts": [
                {"route": "mistral-free", "status": 400, "error_message": "invalid request"}]}))

if __name__ == "__main__": unittest.main()
