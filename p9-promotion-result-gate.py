"""Independent strict result verifier; missing evidence never passes."""
import json
import sys

def failures(d):
    checks = {
        'milestone': d.get('milestone_id') == 'M003.1',
        'patch_exists': d.get('patch_exists') is True,
        'patch_applied': d.get('patch_successfully_applied') is True,
        'resolved': d.get('resolved') is True,
        'fail_closed_build': (d.get('build_failure_policy') or {}).get('fail_closed') is True,
        'no_partial_universe': (d.get('build_failure_policy') or {}).get('partial_test_universe') is False,
        'no_infrastructure_failure': 'infrastructure_failure' in d and not d['infrastructure_failure'],
        'no_infra_invalid': d.get('infra_invalid') is False and 'infra_invalid_reason' in d and not d['infra_invalid_reason'],
        'verified_snapshot': (d.get('snapshot_integrity') or {}).get('ok') is True and (d.get('snapshot_integrity') or {}).get('legacy_unverified') is False,
    }
    e = d.get('evaluation_environment') or {}
    checks.update({
        'repo_config_pinned': e.get('repo_config_binding_mode') == 'trial-pinned' and e.get('repo_config_sha256') == 'cae899cadf1732eefa3c36a057540838ea3ca61739a1267a7da25986c27facec',
        'runtime_policy_pinned': e.get('runtime_policy_binding_mode') == 'trial-pinned' and e.get('runtime_policy_mode') == 'protected' and e.get('runtime_policy_sha256') == 'aa7ec051587f229ac4ac9d3822f2b90790cac551f61a1c284d5664ad45728f1f',
    })
    s = d.get('test_summary') or {}
    for family, expected in [('pass_to_pass', 6954), ('none_to_pass', 1), ('fail_to_pass', 0)]:
        checks[family] = s.get(family+'_required') == expected and s.get(family+'_achieved') == expected
    for key in ['pass_to_pass_failed', 'pass_to_pass_missing', 'none_to_pass_missing']:
        checks[key] = s.get(key) == 0
    return [name for name, ok in checks.items() if not ok]

if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as f:
        errors = failures(json.load(f))
    print(json.dumps({'promotionContractPass':not errors, 'failures':errors}))
    sys.exit(bool(errors))
