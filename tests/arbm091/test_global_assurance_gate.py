import unittest
from arbm_global_assurance_gate import PILLARS, inspect_repo, summarize, require_release_ready


class GlobalAssuranceGateTests(unittest.TestCase):
    def test_all_16_pillars_are_green_with_zero_unknown_and_zero_waiver(self):
        rows=inspect_repo(".")
        result=summarize(rows)
        self.assertEqual(len(PILLARS),16)
        self.assertEqual(result["status"],"RELEASE_READY",result)
        self.assertEqual(result["pass"],16,result)
        self.assertEqual(result["unknown"],0,result)
        self.assertEqual(result["waivers"],0,result)
        self.assertEqual(result["failed"],[],result)
        self.assertFalse(result["certification_claimed"])

    def test_global_gate_is_fail_closed(self):
        rows=list(inspect_repo("."))
        first=rows[0]
        rows[0]=type(first)(
            name=first.name,passed=False,evidence=first.evidence,
            standards=first.standards,unknown=False,waiver=False)
        result=summarize(rows)
        self.assertEqual(result["status"],"BLOCKED")
        self.assertIn(first.name,result["failed"])

    def test_reference_frameworks_are_explicit(self):
        refs={ref for _name,standards in PILLARS for ref in standards}
        for required in (
            "ISO/IEC 42001","ISO/IEC 23894","NIST AI RMF","NIST AI 600-1",
            "NIST CSF 2.0","NIST SSDF SP 800-218","OWASP LLM Top 10 2025",
            "SLSA v1.1","LGPD Art. 46",
        ):
            self.assertIn(required,refs)

    def test_release_ready_function_matches_repository_state(self):
        result=require_release_ready(".")
        self.assertEqual(result["status"],"RELEASE_READY")
        self.assertEqual(result["pass"],16)


if __name__=="__main__":
    unittest.main()
