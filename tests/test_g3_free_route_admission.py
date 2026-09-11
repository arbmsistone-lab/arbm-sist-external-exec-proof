import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'certification'))
from g3_free_route_admission import assess_groq


class IndependentRouteAdmissionTests(unittest.TestCase):
    def test_existing_openrouter_key_cannot_admit_independent_provider(self):
        result = assess_groq(['OPENROUTER_API_KEY', 'HF_TOKEN'])
        self.assertIn('WORKFLOW_CREDENTIAL_MISSING', result['blockers'])
        self.assertFalse(result['inference_admitted'])
        self.assertFalse(result['vm_admitted'])
        self.assertEqual(result['inference_calls'], 0)

    def test_key_presence_and_public_free_label_are_not_account_proof(self):
        result = assess_groq(['GROQ_G3_FREE_CERT_KEY'])
        self.assertIn('AUTHENTICATED_ACCOUNT_FREE_PLAN_NOT_VERIFIED', result['blockers'])
        self.assertEqual(result['state'], 'BLOCKED')

    def test_paid_stale_and_naive_time_evidence_fail_closed(self):
        now = datetime.now(timezone.utc)
        for date, plan in ((now, 'Developer'), (now - timedelta(hours=2), 'Free'),
                           (now.replace(tzinfo=None), 'Free')):
            with self.subTest(date=date, plan=plan):
                receipt = {'source': 'https://console.groq.com/settings/billing',
                           'observed_at_utc': date.isoformat(), 'observed_plan': plan,
                           'paid_usage_enabled': False, 'key_account_binding_verified': True,
                           'remaining_quota_verified': True}
                result = assess_groq(['GROQ_G3_FREE_CERT_KEY'], receipt, now)
                self.assertIn('ACCOUNT_EVIDENCE_INVALID_OR_STALE', result['blockers'])

    def test_account_receipt_never_substitutes_real_probe(self):
        now = datetime.now(timezone.utc)
        receipt = {'source': 'https://console.groq.com/settings/billing',
                   'observed_at_utc': now.isoformat(), 'observed_plan': 'Free',
                   'paid_usage_enabled': False, 'key_account_binding_verified': True,
                   'remaining_quota_verified': True}
        result = assess_groq(['GROQ_G3_FREE_CERT_KEY'], receipt, now)
        self.assertFalse(result['inference_admitted'])
        self.assertIn('LIVE_CAPABILITY_PROBE_NOT_RUN', result['blockers'])
        self.assertFalse(result['automatic_model_fallback'])


if __name__ == '__main__':
    unittest.main()
