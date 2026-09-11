"""Read-only admission for independent FREE routes. Never sends inference."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


GROQ_ROUTE = {
    'route_id': 'groq-qwen3.8-27b-free',
    'provider': 'groq',
    'independence_group': 'groq',
    'model': 'qwen/qwen3.8-27b',
    'base_url': 'https://api.groq.com/openai/v1',
    'secret_name': 'GROQ_G3_FREE_CERT_KEY',
    'billing_plan_required': 'Free',
    'capabilities_advertised': ['IMAGE', 'TOOL_CALLING', 'CONTEXT'],
    'limits_are_public_defaults_not_account_balance': True,
    'published_limits': {'rpm': 30, 'rpd': 1000, 'tpm': 8000, 'tpd': 200000},
    'public_sources': [
        'https://console.groq.com/docs/vision',
        'https://console.groq.com/docs/tool-use/overview',
        'https://console.groq.com/docs/rate-limits',
        'https://console.groq.com/docs/billing-faqs',
    ],
}


def assess_groq(secret_names, account_receipt=None, now=None):
    """Configuration is never provider proof. The new transport stays disabled."""
    blockers = []
    if GROQ_ROUTE['secret_name'] not in secret_names:
        blockers.append('WORKFLOW_CREDENTIAL_MISSING')
    if account_receipt is None:
        blockers.append('AUTHENTICATED_ACCOUNT_FREE_PLAN_NOT_VERIFIED')
    else:
        # Only a fresh provider-account observation qualifies for further review.
        # A user flag, catalog pricing, or a key name cannot establish the plan.
        try:
            observed = datetime.fromisoformat(account_receipt['observed_at_utc'])
            age = ((now or datetime.now(timezone.utc)) - observed).total_seconds()
            valid = (0 <= age <= 3600 and
                     account_receipt.get('source') == 'https://console.groq.com/settings/billing' and
                     account_receipt.get('observed_plan') == 'Free' and
                     account_receipt.get('paid_usage_enabled') is False and
                     account_receipt.get('key_account_binding_verified') is True and
                     account_receipt.get('remaining_quota_verified') is True)
        except (KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            blockers.append('ACCOUNT_EVIDENCE_INVALID_OR_STALE')
    # There is deliberately no execution bypass. Authenticated account proof,
    # an audited provider transport and a real capability probe are still needed.
    blockers.extend(['PROVIDER_TRANSPORT_NOT_CERTIFIED', 'LIVE_CAPABILITY_PROBE_NOT_RUN'])
    return {
        **GROQ_ROUTE, 'state': 'BLOCKED', 'blockers': blockers,
        'inference_admitted': False, 'vm_admitted': False,
        'inference_calls': 0, 'vms_prepared': 0, 'new_spend_usd': 0,
        'ZERO_SPEND': True, 'HEAVY_LOCAL': 0,
        'automatic_model_fallback': False,
        'human_microaction': 'Sign in at https://console.groq.com/keys using the ARBM owner account; keep the Free plan.',
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--secret-names-json', type=Path, required=True)
    parser.add_argument('--account-receipt', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # This input contains names only, obtained using gh secret list --json name.
    names = [row['name'] for row in json.loads(args.secret_names_json.read_text())]
    receipt = json.loads(args.account_receipt.read_text()) if args.account_receipt else None
    report = assess_groq(names, receipt)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'state': report['state'], 'blockers': report['blockers'],
                      'inference_calls': 0, 'vms_prepared': 0}))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
