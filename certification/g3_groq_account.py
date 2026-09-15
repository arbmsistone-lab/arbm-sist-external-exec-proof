"""Fresh account evidence, credential association and read-only Groq admission.

The console exposes a masked suffix, not a full-key fingerprint. Association is
explicitly labelled as such; authentication subsequently uses the actual key.
No request is admitted by a plan boolean, a key label or missing API cost alone.
"""
import hashlib
import hmac
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

MODEL = 'qwen/qwen3.8-27b'


def account_contract(key=None, receipt=None, now=None):
    key = os.environ.get('GROQ_G3_FREE_CERT_KEY', '') if key is None else key
    try:
        receipt = json.loads(os.environ.get('G3_GROQ_ACCOUNT_RECEIPT', '{}')) if receipt is None else receipt
        observed = datetime.fromisoformat(receipt['observed_at_utc'])
        age = ((now or datetime.now(timezone.utc)) - observed).total_seconds()
        actual = hashlib.sha256(('g3-groq-ui-v1:' + key[-4:]).encode()).hexdigest()
        valid = (
            0 <= age <= 3600 and key.startswith('gsk_') and len(key) >= 24 and
            receipt.get('source') == 'https://console.groq.com/settings/billing/plans' and
            receipt.get('keys_source') == 'https://console.groq.com/keys' and
            receipt.get('method') == 'AUTHENTICATED_VISIBLE_UI' and
            receipt.get('plan') == 'Free' and receipt.get('current_plan') is True and
            receipt.get('displayed_price') == '$0' and
            receipt.get('model') == MODEL and receipt.get('key_label') == 'ARBM-SIST-G3-FREE-CERT-20260911' and
            hmac.compare_digest(actual, receipt.get('masked_suffix_sha256', '')))
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise RuntimeError('G3_FREE_GROQ_ACCOUNT_PROOF_REQUIRED')
    return {'provider': 'groq', 'plan': 'Free', 'source': receipt['source'],
            'observed_at_utc': receipt['observed_at_utc'],
            'association_method': 'AUTHENTICATED_CONSOLE_MASKED_SUFFIX_MATCH',
            'full_key_identity_proven_by_console': False,
            'account_receipt_sha256': hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest(),
            'contractual_cost_usd': '0', 'remaining_quota_proven': False}


def catalog_admission():
    proof = account_contract()
    req = urllib.request.Request('https://api.groq.com/openai/v1/models', headers={
        'Authorization': 'Bearer ' + os.environ['GROQ_G3_FREE_CERT_KEY'],
        'Accept': 'application/json', 'User-Agent': 'ARBM-G3-FREE-admission/2.0'})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError('G3_FREE_GROQ_CATALOG_HTTP_' + str(error.code)) from None
    item = next((r for r in data.get('data', []) if r.get('id') == MODEL), None)
    if not item or item.get('active') is not True or item.get('context_window', 0) < 32768:
        raise RuntimeError('G3_FREE_GROQ_MODEL_NOT_AVAILABLE')
    return {**proof, 'id': MODEL, 'credential_authenticated': True,
            'context_length': item['context_window'], 'inference_calls': 0}


def quota_headers(headers):
    allowed = ('x-ratelimit-limit-requests', 'x-ratelimit-remaining-requests',
               'x-ratelimit-reset-requests', 'x-ratelimit-limit-tokens',
               'x-ratelimit-remaining-tokens', 'x-ratelimit-reset-tokens')
    return {k: str(headers[k]) for k in allowed if k in headers and
            re.fullmatch(r'[0-9.hms]+', str(headers[k]))}


def reset_seconds(value):
    parts = re.findall(r'(\d+(?:\.\d+)?)(ms|h|m|s)', value)
    if not parts or ''.join(n + unit for n, unit in parts) != value:
        raise RuntimeError('G3_FREE_GROQ_QUOTA_RESET_INVALID')
    return sum(float(n) * {'ms': .001, 's': 1, 'm': 60, 'h': 3600}[unit] for n, unit in parts)


def pace_quota(headers, received_at, reserve_tokens, *, now=None):
    """Delay only for an observed token-window deficit; terminal quota gets no retry."""
    if not headers:
        return 0.0
    try:
        remaining_requests = int(headers['x-ratelimit-remaining-requests'])
        remaining_tokens = int(headers['x-ratelimit-remaining-tokens'])
        limit = int(headers['x-ratelimit-limit-tokens'])
        if remaining_requests < 1 or reserve_tokens > limit:
            raise RuntimeError('G3_FREE_GROQ_QUOTA_INSUFFICIENT')
        if remaining_tokens >= reserve_tokens:
            return 0.0
        reset = reset_seconds(headers['x-ratelimit-reset-tokens'])
        delay = max(0.0, received_at + reset + .25 - (time.monotonic() if now is None else now))
        if delay > 60:
            raise RuntimeError('G3_FREE_GROQ_QUOTA_RESET_TOO_LONG')
        return delay
    except (KeyError, TypeError, ValueError):
        raise RuntimeError('G3_FREE_GROQ_QUOTA_NOT_PROVEN') from None
