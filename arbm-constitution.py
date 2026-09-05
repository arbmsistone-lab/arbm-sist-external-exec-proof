"""Technical P8 invariants only. Policy PASS does not certify a benchmark."""
import json
import os

REQUIRED = {
    'zeroSpendMode': 'HARD',
    'paidInferenceAllowed': False,
    'publicSourceOnly': True,
    'officialEvaluatorRequired': True,
    'failClosed': True,
}


def validate(policy, mode='HARD'):
    if not isinstance(policy, dict):
        return ['CONSTITUTION_VIOLATION:INVALID_POLICY']
    reasons = []
    for key, expected in REQUIRED.items():
        actual = policy.get(key)
        if type(actual) is not type(expected) or actual != expected:
            reasons.append('CONSTITUTION_VIOLATION:' + key)
    if mode != 'HARD':
        reasons.append('CONSTITUTION_VIOLATION:ZERO_SPEND_MODE')
    return reasons


if __name__ == '__main__':
    reasons = validate(REQUIRED, os.environ.get('ZERO_SPEND_MODE', 'HARD'))
    print(json.dumps({'gate': 'p8-technical-policy', 'status': 'NO-GO' if reasons else 'PASS',
                      'reasons': reasons, 'benchmarkApproved': False}))
    raise SystemExit(1 if reasons else 0)
