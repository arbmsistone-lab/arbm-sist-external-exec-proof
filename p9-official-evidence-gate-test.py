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


if __name__=='__main__':
    unittest.main()
