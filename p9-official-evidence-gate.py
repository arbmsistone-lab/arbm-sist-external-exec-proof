"""Fail closed on solver-only evidence; never certify a partial test universe."""
import json
from pathlib import Path
import sys


def validate_evaluator(result):
    failures=[]
    def require(condition, name):
        if not condition:
            failures.append(name)
    require(result.get('milestone_id') == 'M003.1', 'milestone_identity')
    for name in ('patch_exists','patch_successfully_applied','resolved'):
        require(result.get(name) is True, name)
    require((result.get('build_failure_policy') or {}).get('fail_closed') is True, 'fail_closed_build_policy')
    require(not result.get('infrastructure_failure'), 'infrastructure_failure')
    require(not result.get('infra_invalid_reason'), 'infra_invalid_reason')
    summary=result.get('test_summary') or {}
    for family, required in [('fail_to_pass',0),('none_to_pass',1),('pass_to_pass',6954)]:
        require(type(summary.get(family+'_required')) is int and summary[family+'_required']==required, family+'_required')
        require(type(summary.get(family+'_achieved')) is int and summary[family+'_achieved']==required, family+'_achieved')
    for name in ('pass_to_pass_failed','pass_to_pass_missing','none_to_pass_missing'):
        require(type(summary.get(name)) is int and summary[name]==0,name)
    return failures


def validate_artifact(root):
    result_path=root/'evaluation_result.json'
    if not result_path.is_file():
        return ['OFFICIAL_EVALUATOR_EVIDENCE_MISSING']
    failures=validate_evaluator(json.loads(result_path.read_text(encoding='utf-8')))
    # Native official-trial evidence is mandatory; a solver response cannot replace it.
    for name in ('trial_metadata.json','dag_state.json','agent.log','submitted.patch','SHA256SUMS.txt'):
        p=root/name
        if not p.is_file() or not p.stat().st_size:
            failures.append('CLEAN_OFFICIAL_TRIAL_EVIDENCE_MISSING:'+name)
    if not failures:
        # No reviewed native trial importer exists in this solver-only workflow yet.
        # Do not infer the 15-link P9 chain from file presence or synthetic flags.
        failures.append('P9_NATIVE_TRIAL_CHAIN_VERIFICATION_REQUIRED')
    return failures


if __name__=='__main__':
    failures=validate_artifact(Path(sys.argv[1]))
    print(json.dumps({'p9OfficialPass':False,'failures':failures},sort_keys=True))
    raise SystemExit(1 if failures else 0)
