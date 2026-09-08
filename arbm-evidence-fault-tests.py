import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

ev=load('ev','arbm-evidence-pack.py')
fi=load('fi','arbm-fault-injection.py')

class Tests(unittest.TestCase):
    def valid_pack(self):
        return {'candidate_sha':'abc','mission_id':'m1','executor_provider':'github','ai_provider':'google-gemini','input_sha256':'1'*64,'output_sha256':'2'*64,'tests':{'passed':1,'failed':0},'mandatory_cost_usd':0,'started_at':'2026-09-08T10:00:00-03:00','finished_at':'2026-09-08T10:01:00-03:00'}

    def test_pack_free_and_green(self):
        self.assertEqual(ev.validate_pack(self.valid_pack()),[])

    def test_pack_blocks_cost(self):
        p=self.valid_pack(); p['mandatory_cost_usd']=0.01
        self.assertIn('mandatory_cost_nonzero',ev.validate_pack(p))

    def test_freeze_is_deterministic(self):
        with tempfile.TemporaryDirectory() as d:
            a=ev.freeze_pack(self.valid_pack(),Path(d)); b=ev.freeze_pack(self.valid_pack(),Path(d))
            self.assertEqual(a['sha256'],b['sha256'])

    def test_recoverable_faults_resume_without_duplicate(self):
        state={'checkpoint':'cp-17','attempts':0,'provider_index':0}
        for fault in fi.RECOVERABLE:
            r=fi.recover(state,fault)
            self.assertEqual(r['status'],'RESUME')
            self.assertEqual(r['resume_from'],'cp-17')
            self.assertFalse(r['duplicate_mutation'])

    def test_provider_rotation_is_three_way(self):
        state={'checkpoint':'cp','attempts':0,'provider_index':2}
        self.assertEqual(fi.recover(state,'provider_timeout')['provider_index'],0)

    def test_corrupt_checkpoint_blocks_fail_closed(self):
        r=fi.recover({'checkpoint':'cp'},'checkpoint_corrupt')
        self.assertEqual(r['status'],'BLOCKED')
        self.assertEqual(r['reason'],'CHECKPOINT_INTEGRITY_FAILURE')

if __name__=='__main__':
    unittest.main()
