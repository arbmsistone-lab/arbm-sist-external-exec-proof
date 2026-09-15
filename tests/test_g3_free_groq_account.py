import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'certification'))
from g3_free_control import journal_report, load_agent
from g3_groq_account import MODEL, account_contract, catalog_admission, pace_quota, quota_headers, reset_seconds


FAKE_KEY = 'gsk_' + 'synthetic-not-a-live-key-0000'


def receipt():
    return {'observed_at_utc': datetime.now(timezone.utc).isoformat(),
            'source': 'https://console.groq.com/settings/billing/plans',
            'keys_source': 'https://console.groq.com/keys',
            'method': 'AUTHENTICATED_VISIBLE_UI', 'plan': 'Free',
            'current_plan': True, 'displayed_price': '$0', 'model': MODEL,
            'key_label': 'ARBM-SIST-G3-FREE-CERT-20260911',
            'masked_suffix_sha256': hashlib.sha256(('g3-groq-ui-v1:' + FAKE_KEY[-4:]).encode()).hexdigest()}


def headers(remaining=7000):
    return {'x-ratelimit-limit-requests': '1000', 'x-ratelimit-remaining-requests': '999',
            'x-ratelimit-limit-tokens': '8000', 'x-ratelimit-remaining-tokens': str(remaining),
            'x-ratelimit-reset-tokens': '7.5s', 'x-ratelimit-reset-requests': '1h2m3s'}


class GroqAccountTests(unittest.TestCase):
    def test_fresh_association_is_not_full_key_or_quota_proof(self):
        proof = account_contract(FAKE_KEY, receipt())
        self.assertEqual(proof['contractual_cost_usd'], '0')
        self.assertFalse(proof['full_key_identity_proven_by_console'])
        self.assertFalse(proof['remaining_quota_proven'])
        self.assertNotIn(FAKE_KEY, json.dumps(proof))
        self.assertNotIn(FAKE_KEY[-4:], json.dumps(proof))

    def test_flags_labels_paid_plan_and_other_key_cannot_admit(self):
        for field, value in [('plan', 'Developer'), ('current_plan', False),
                             ('displayed_price', 'Pay per Token'), ('method', 'USER_FLAG'),
                             ('key_label', 'OTHER'), ('source', 'https://example.com'),
                             ('masked_suffix_sha256', '0' * 64)]:
            with self.subTest(field=field):
                with self.assertRaisesRegex(RuntimeError, 'ACCOUNT_PROOF_REQUIRED'):
                    account_contract(FAKE_KEY, {**receipt(), field: value})
        with self.assertRaisesRegex(RuntimeError, 'ACCOUNT_PROOF_REQUIRED'):
            account_contract(FAKE_KEY + 'x', receipt())

    def test_stale_future_naive_and_malformed_receipts_block(self):
        now = datetime.now(timezone.utc)
        dates = [(now - timedelta(hours=2)).isoformat(), (now + timedelta(seconds=10)).isoformat(),
                 now.replace(tzinfo=None).isoformat(), 'bad']
        for date in dates:
            with self.assertRaisesRegex(RuntimeError, 'ACCOUNT_PROOF_REQUIRED'):
                account_contract(FAKE_KEY, {**receipt(), 'observed_at_utc': date}, now)
        for bad in ({}, [], None):
            with patch.dict(os.environ, {'G3_GROQ_ACCOUNT_RECEIPT': '{}'}):
                with self.assertRaisesRegex(RuntimeError, 'ACCOUNT_PROOF_REQUIRED'):
                    account_contract(FAKE_KEY, bad)

    def test_catalog_authentication_is_read_only_and_requires_active_model(self):
        response = io.BytesIO(json.dumps({'data': [{'id': MODEL, 'active': True,
                                                  'context_window': 262144}]}).encode())
        env = {'G3_GROQ_ACCOUNT_RECEIPT': json.dumps(receipt()), 'GROQ_G3_FREE_CERT_KEY': FAKE_KEY}
        with patch.dict(os.environ, env), patch('urllib.request.urlopen', return_value=response) as fetch:
            proof = catalog_admission()
        request = fetch.call_args.args[0]
        self.assertEqual(request.get_method(), 'GET')
        self.assertEqual(request.full_url, 'https://api.groq.com/openai/v1/models')
        self.assertTrue(proof['credential_authenticated'])
        self.assertEqual(proof['inference_calls'], 0)

    def test_no_request_with_invalid_account_receipt(self):
        with patch.dict(os.environ, {'G3_GROQ_ACCOUNT_RECEIPT': '{}'}):
            with patch('urllib.request.urlopen') as fetch:
                with self.assertRaisesRegex(RuntimeError, 'ACCOUNT_PROOF_REQUIRED'):
                    catalog_admission()
                fetch.assert_not_called()

    def test_quota_pacing_uses_actual_window_deficit(self):
        self.assertEqual(pace_quota(headers(), 100, 3000, now=101), 0)
        self.assertEqual(pace_quota(headers(500), 100, 3000, now=101), 6.75)
        self.assertEqual(pace_quota(headers(500), 100, 3000, now=110), 0)

    def test_exhausted_request_quota_is_terminal(self):
        with self.assertRaisesRegex(RuntimeError, 'QUOTA_INSUFFICIENT'):
            pace_quota({**headers(), 'x-ratelimit-remaining-requests': '0'}, 100, 3000, now=101)

    def test_oversize_missing_and_long_reset_quota_block(self):
        with self.assertRaisesRegex(RuntimeError, 'QUOTA_INSUFFICIENT'):
            pace_quota(headers(), 100, 8001, now=101)
        with self.assertRaisesRegex(RuntimeError, 'QUOTA_NOT_PROVEN'):
            pace_quota({'x-ratelimit-limit-tokens': '8000'}, 100, 3000, now=101)
        with self.assertRaisesRegex(RuntimeError, 'QUOTA_RESET_TOO_LONG'):
            pace_quota({**headers(0), 'x-ratelimit-reset-tokens': '2m'}, 100, 3000, now=101)

    def test_header_allowlist_and_duration_units(self):
        self.assertEqual(quota_headers({**headers(), 'authorization': 'never record'}), headers())
        self.assertEqual(reset_seconds('1m2.5s'), 62.5)
        self.assertEqual(reset_seconds('500ms'), .5)
        with self.assertRaisesRegex(RuntimeError, 'RESET_INVALID'):
            reset_seconds('1s<script>')

    def test_authenticated_missing_cost_remains_null_and_contract_is_separate(self):
        agent_module = load_agent()
        action = {'action': 'click', 'parameters': {'x': 500, 'y': 500},
                  'state_summary': 'Visible synthetic button.', 'target': 'Button',
                  'expected_change': 'Button becomes selected.'}
        data = {'model': MODEL, 'usage': {'prompt_tokens': 200, 'completion_tokens': 80,
                                        'total_tokens': 280},
                'choices': [{'finish_reason': 'tool_calls', 'message': {'content': None,
                    'tool_calls': [{'id': 'synthetic-call', 'type': 'function', 'function': {
                        'name': 'desktop_action', 'arguments': json.dumps(action)}}]}}]}
        raw = SimpleNamespace(headers=headers(), parse=lambda: SimpleNamespace(model_dump=lambda: data.copy()))
        with tempfile.TemporaryDirectory() as temp:
            log = Path(temp) / 'usage.jsonl'
            env = {'G3_GROQ_ACCOUNT_RECEIPT': json.dumps(receipt()), 'GROQ_G3_FREE_CERT_KEY': FAKE_KEY,
                   'ARBM_G3_FREE_MODEL': MODEL, 'ARBM_G3_PROVIDER': 'groq', 'ARBM_G3_USAGE_LOG': str(log)}
            with patch.dict(os.environ, env), patch('openai.OpenAI') as constructor:
                constructor.return_value.chat.completions.with_raw_response.create.return_value = raw
                agent = agent_module.ArbmG3Agent()
                image = io.BytesIO()
                Image.new('RGB', (400, 240), 'white').save(image, format='PNG')
                _, commands = agent.predict('Select the visible button.', {'screenshot': image.getvalue()})
            self.assertEqual(commands, ['pyautogui.click(x=200, y=120)'])
            self.assertEqual(constructor.call_args.kwargs['max_retries'], 0)
            terminal = json.loads(log.read_text().splitlines()[-1])
            self.assertIsNone(terminal['reported_cost_usd'])
            self.assertIsNone(terminal['usage']['cost'])
            self.assertEqual(terminal['contractual_cost_usd'], '0')
            self.assertEqual(terminal['quota_headers'], headers())
            audit = journal_report(log)
            self.assertTrue(audit['accounting_complete'])
            self.assertTrue(audit['all_calls_zero_spend_proven'])
            self.assertFalse(audit['all_calls_observed_zero_cost'])


if __name__ == '__main__':
    unittest.main()
