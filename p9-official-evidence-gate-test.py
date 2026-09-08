import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('gate',Path(__file__).with_name('p9-official-evidence-gate.py'))
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class ContractTests(unittest.TestCase):
    def valid(self):
        return {'milestone_id':'M003.1','patch_exists':True,'patch_successfully_applied':True,
                'resolved':True,'build_failure_policy':{'fail_closed':True},
                'test_summary':{'fail_to_pass_required':0,'fail_to_pass_achieved':0,
                    'none_to_pass_required':1,'none_to_pass_achieved':1,
                    'pass_to_pass_required':6954,'pass_to_pass_achieved':6954,
                    'pass_to_pass_failed':0,'pass_to_pass_missing':0,'none_to_pass_missing':0}}

    def test_full_evaluator_contract(self):
        self.assertEqual(gate.validate_evaluator(self.valid()),[])

    def test_zero_tests_and_infra_invalid_never_pass(self):
        result=self.valid()
        result['infra_invalid_reason']='zero-tests-with-required-tests'
        result['test_summary']['pass_to_pass_achieved']=0
        self.assertIn('infra_invalid_reason',gate.validate_evaluator(result))
        self.assertIn('pass_to_pass_achieved',gate.validate_evaluator(result))

    def test_partial_universe_even_if_resolved_rejected(self):
        result=self.valid()
        result['test_summary']['pass_to_pass_required']=10
        result['test_summary']['pass_to_pass_achieved']=10
        self.assertIn('pass_to_pass_required',gate.validate_evaluator(result))

    def test_absent_counters_do_not_default_to_zero(self):
        result=self.valid()
        del result['test_summary']['none_to_pass_missing']
        self.assertIn('none_to_pass_missing',gate.validate_evaluator(result))

    def test_boolean_is_not_a_counter(self):
        result=self.valid()
        result['test_summary']['none_to_pass_achieved']=True
        self.assertIn('none_to_pass_achieved',gate.validate_evaluator(result))

    def test_solver_success_is_not_official_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'solve-evidence.json').write_text('{"state":"SUCCEEDED"}')
            self.assertEqual(gate.validate_artifact(root),['OFFICIAL_EVALUATOR_EVIDENCE_MISSING'])

    def test_promotion_pack_is_native_official_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'solve-artifact').mkdir()
            (root/'promotion-summary.json').write_text('{"schema":"arbm-p9-official-promotion-v1","task":"dubbo/M003.1","promotionGrade":true,"resolved":true,"snapshotIntegrityOk":true,"zeroSpendMode":"HARD","infraInvalid":false}')
            (root/'evaluation_result.json').write_text(__import__('json').dumps(self.valid()))
            (root/'source_snapshot.integrity.json').write_text('{"ok":true,"gold_patch_exposed":false}')
            (root/'solve-artifact'/'solve-evidence.json').write_text('{"state":"SUCCEEDED","zeroSpendMode":"HARD","mandatoryCostUsd":0,"executionType":"remote","goldPatchExposed":false}')
            for rel in ('solve-artifact/SHA256SUMS.txt','source_snapshot.tar.sha256','evaluation-SHA256SUMS.txt'):
                (root/rel).write_text('proof')
            self.assertEqual(gate.validate_artifact(root),[])


if __name__=='__main__':
    unittest.main()
