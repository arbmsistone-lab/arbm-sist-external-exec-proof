"""Frozen mandate validation. PASS here is policy validity, never release approval."""
import hashlib
import json
import os
from pathlib import Path

REQUIRED = {
    'schema': 'arbm-constitution-v1', 'zeroSpendMode': 'HARD', 'mandatoryCostBRL': 0,
    'preserveV10': True, 'providerIndependent': True, 'secretsOutsideModels': True,
    'failClosed': True, 'automaticBilling': False, 'automaticOverage': False,
    'zeroPriceBRL': 0, 'proPriceBRL': 1197, 'continuityPriceBRL': 79.90,
    'continuityFirstBillingMonth': 13, 'stableLicensePersists': True,
    'boostTargetPriceBRL': 19.90, 'boostMaxManagedMonthlyCostBRL': 7,
    'boostCommercialEnabled': False, 'byokIncluded': True,
    'zeroIntentionallyDegraded': False, 'newToStableAllowed': False,
    'distinctGeneratorCriticReleaseAuthority': True, 'externalProofRequiredForTop3': True,
}


def validate(policy, mode='HARD'):
    reasons = []
    if not isinstance(policy, dict):
        return ['CONSTITUTION_VIOLATION:INVALID_POLICY']
    for key, value in REQUIRED.items():
        actual = policy.get(key)
        if type(actual) is not type(value) or actual != value:
            reasons.append('CONSTITUTION_VIOLATION:' + key)
    if mode != 'HARD':
        reasons.append('CONSTITUTION_VIOLATION:ZERO_SPEND_MODE')
    return reasons


def main():
    root = Path(__file__).resolve().parent
    try:
        policy = json.loads((root/'arbm-constitution.json').read_text(encoding='utf-8'))
        reasons = validate(policy, os.environ.get('ZERO_SPEND_MODE', 'HARD'))
        actual = hashlib.sha256((root/'ARBM-SIST-MANDATE.md').read_text(encoding='utf-8').encode('utf-8')).hexdigest()
        if actual != policy.get('mandateSha256'):
            reasons.append('CONSTITUTION_VIOLATION:MANDATE_HASH')
    except (OSError, ValueError, TypeError):
        reasons = ['CONSTITUTION_VIOLATION:UNREADABLE_POLICY']
    print(json.dumps({'gate': 'constitution-policy', 'status': 'NO-GO' if reasons else 'PASS',
                      'reasons': reasons, 'technicalRelease': 'NO-GO',
                      'worldClassReadiness': 'NOT VERIFIED', 'globalTop3ZeroCost': 'NOT CERTIFIED'}))
    return 1 if reasons else 0


if __name__ == '__main__':
    raise SystemExit(main())
