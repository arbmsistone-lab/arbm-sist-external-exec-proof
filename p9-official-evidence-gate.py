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
    promo=root/'promotion-summary.json'
    if promo.is_file():
        failures=[]
        summary=json.loads(promo.read_text(encoding='utf-8'))
        checks=[
            (summary.get('schema')=='arbm-p9-official-promotion-v1','promotion_schema'),
            (summary.get('task')=='dubbo/M003.1','promotion_task'),
            (summary.get('promotionGrade') is True,'promotion_grade'),
            (summary.get('resolved') is True,'promotion_resolved'),
            (summary.get('snapshotIntegrityOk') is True,'snapshot_integrity_ok'),
            (summary.get('zeroSpendMode')=='HARD','promotion_zero_spend'),
            (summary.get('infraInvalid') is False,'promotion_infra_valid')]
        failures += [name for ok,name in checks if not ok]
        result_path=root/'evaluation_result.json'
        if not result_path.is_file(): failures.append('OFFICIAL_EVALUATOR_EVIDENCE_MISSING')
        else: failures += validate_evaluator(json.loads(result_path.read_text(encoding='utf-8')))
        integrity_path=root/'source_snapshot.integrity.json'
        if not integrity_path.is_file(): failures.append('SOURCE_SNAPSHOT_INTEGRITY_MISSING')
        else:
            integrity=json.loads(integrity_path.read_text(encoding='utf-8'))
            if integrity.get('ok') is not True: failures.append('SOURCE_SNAPSHOT_INTEGRITY_FAILED')
            if integrity.get('gold_patch_exposed') is not False: failures.append('GOLD_PATCH_EXPOSURE_NOT_FALSE')
        solve_path=root/'solve-artifact'/'solve-evidence.json'
        if not solve_path.is_file(): failures.append('SOLVE_EVIDENCE_MISSING')
        else:
            solve=json.loads(solve_path.read_text(encoding='utf-8'))
            required=[(solve.get('state')=='SUCCEEDED','solve_state'),(solve.get('zeroSpendMode')=='HARD','solve_zero_spend'),(solve.get('mandatoryCostUsd')==0,'solve_cost'),(solve.get('executionType')=='remote','solve_remote'),(solve.get('goldPatchExposed') is False,'solve_gold_patch')]
            failures += [name for ok,name in required if not ok]
        for rel in ('solve-artifact/SHA256SUMS.txt','source_snapshot.tar.sha256','evaluation-SHA256SUMS.txt'):
            if not (root/rel).is_file(): failures.append('PROMOTION_HASH_EVIDENCE_MISSING:'+rel)
        return failures
    result_path=root/'evaluation_result.json'
    if not result_path.is_file(): return ['OFFICIAL_EVALUATOR_EVIDENCE_MISSING']
    return validate_evaluator(json.loads(result_path.read_text(encoding='utf-8'))) + ['P9_NATIVE_TRIAL_CHAIN_VERIFICATION_REQUIRED']


if __name__=='__main__':
    failures=validate_artifact(Path(sys.argv[1]))
    print(json.dumps({'p9OfficialPass':False,'failures':failures},sort_keys=True))
    raise SystemExit(1 if failures else 0)
