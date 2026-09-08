import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("top3gate", ROOT / "top3-certification-gate.py")
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


class Top3CertificationGateTests(unittest.TestCase):
    def manifest(self):
        return json.loads((ROOT / "top3-certification-manifest.json").read_text(encoding="utf-8"))

    def test_current_manifest_is_fail_closed(self):
        failures = GATE.validate_manifest(self.manifest())
        self.assertIn("gate_not_pass:terminal_benchmark:PENDING_EXTERNAL_PROOF", failures)
        self.assertIn("gate_not_pass:computer_use_benchmark:PENDING_EXTERNAL_PROOF", failures)
        self.assertIn("gate_not_pass:three_independent_runners:PENDING_3X_E2E_PROOF", failures)
        self.assertIn("gate_not_pass:universal_evidence_pack:PENDING_INTEGRATED_PROOF", failures)
        self.assertNotIn("gate_not_pass:ai_three_independent_providers:PASS", failures)
        self.assertNotIn("gate_not_pass:distributed_recovery:PASS", failures)
        self.assertNotIn("gate_not_pass:remote_cancel_preempt:PASS", failures)
        self.assertNotIn("gate_not_pass:context_isolation:PASS", failures)
        self.assertNotIn("gate_not_pass:long_missions:PASS", failures)

    def test_engineering_official_proof_is_accepted(self):
        failures = GATE.validate_manifest(self.manifest())
        self.assertNotIn("gate_not_pass:official_engineering_evaluator:PASS", failures)
        self.assertNotIn("engineering_resolved", failures)
        self.assertNotIn("engineering_pass_to_pass", failures)
    def test_all_pass_can_certify(self):
        manifest = self.manifest()
        for gate in manifest["gates"].values():
            gate["status"] = "PASS"
        self.assertEqual(GATE.validate_manifest(manifest), [])

    def test_cost_or_digest_regression_blocks(self):
        manifest = self.manifest()
        for gate in manifest["gates"].values():
            gate["status"] = "PASS"
        manifest["mandatory_cost_usd"] = 1
        manifest["gates"]["official_engineering_evaluator"]["artifact_digest"] = "bad"
        failures = GATE.validate_manifest(manifest)
        self.assertIn("mandatory_cost_usd", failures)
        self.assertIn("engineering_artifact_digest", failures)

    def test_missing_gate_blocks(self):
        manifest = self.manifest()
        del manifest["gates"]["context_isolation"]
        self.assertIn("missing_gate:context_isolation", GATE.validate_manifest(manifest))


if __name__ == "__main__":
    unittest.main()
