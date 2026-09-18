import copy
import json
from pathlib import Path
import unittest

from master_supreme_assurance_gate import validate_manifest, validate_registry


ROOT=Path(__file__).resolve().parents[1]
REG=json.loads((ROOT/"assurance/master-supreme/gate-registry.json").read_text())
MAN=json.loads((ROOT/"assurance/master-supreme/evidence-manifest.json").read_text())


class MasterSupremeAssuranceTests(unittest.TestCase):
    def test_current_ledger_is_fail_closed_and_structurally_valid(self):
        self.assertEqual(validate_registry(REG),[])
        self.assertEqual(validate_manifest(MAN,REG),[])

    def test_pass_requires_evidence(self):
        data=copy.deepcopy(REG)
        g=next(x for x in data["gates"] if x["id"]=="G-REGRESSION")
        g.pop("evidence",None)
        self.assertIn("PASS_WITHOUT_EVIDENCE:G-REGRESSION",validate_registry(data))

    def test_blocked_requires_cause(self):
        data=copy.deepcopy(REG)
        g=next(x for x in data["gates"] if x["id"]=="G-091-OFFICIAL")
        g.pop("cause",None)
        self.assertIn("BLOCKED_WITHOUT_CAUSE:G-091-OFFICIAL",validate_registry(data))

    def test_final_signoff_cannot_bypass_open_gates(self):
        data=copy.deepcopy(REG)
        final=next(x for x in data["gates"] if x["id"]=="G-FINAL-SIGNOFF")
        final["state"]="PASS"; final["evidence"]="synthetic-test"
        errors=validate_registry(data)
        self.assertTrue(any(x.startswith("PASS_WITH_UNMET_DEPENDENCY:G-FINAL-SIGNOFF") or
                            x.startswith("FINAL_SIGNOFF_WITH_OPEN_GATE:") for x in errors))

    def test_manifest_pass_must_match_frozen_sha(self):
        man=copy.deepcopy(MAN)
        e=next(x for x in man["evidence"] if x["state"]=="PASS")
        e["commit_sha"]="0"*40
        self.assertTrue(any(x.startswith("EVIDENCE_PASS_SHA_MISMATCH") for x in validate_manifest(man,REG)))

    def test_certification_pass_requires_final_signoff(self):
        man=copy.deepcopy(MAN); man["certification_state"]="PASS"
        self.assertIn("CERTIFICATION_PASS_WITHOUT_FINAL_SIGNOFF",validate_manifest(man,REG))


if __name__=="__main__":
    unittest.main()
