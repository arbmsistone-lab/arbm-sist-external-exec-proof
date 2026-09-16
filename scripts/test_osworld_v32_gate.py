import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from osworld_evidence import seal
from osworld_v32_gate import aggregate, audit_task, PINS, SHARDS


class OfficialGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = patch('osworld_v32_gate.Path', wraps=Path)
        self.path_mock = self.output.start(); self.addCleanup(self.output.stop)
        self.path_mock.side_effect = lambda name: self.root / name
        for tasks in SHARDS.values():
            for task in tasks: self.fixture(task)

    def fixture(self, task):
        d = self.root / ('task-' + task); d.mkdir()
        values = {'task-id.txt':task, 'candidate-sha.txt':'test-sha', 'release.txt':PINS['release'],
            'max-steps.txt':'500', 'task-rc.txt':'0', 'zero-spend-mode.txt':'HARD',
            'runner-environment.txt':'github-hosted', 'osworld.log':('File downloaded successfully\nfound_edited_photo=1 (path=/home/user/Pictures/IMG_7318_edited.jpg)' if task=='061' else 'unit fixture; not benchmark evidence'),
            'shim-runtime.log':'unit fixture', 'pins.json':json.dumps(PINS),
            'evaluator-integrity.json':json.dumps({'task.py':{'before':'hash','after':'hash'}}),
            'shim.jsonl':json.dumps({'commit':'test-sha','task_id':task,'http':200,'mandatory_cost_usd':0,
                'paid_fallback_used':False,'provider_attempts':[{'status':200,'free_plan_proven':True}],
                'status':'ACTION_ISSUED'})}
        for name, content in values.items(): (d / name).write_text(content)
        r = d / 'results' / 'tasks' / task; r.mkdir(parents=True)
        (r / 'result.txt').write_text('1.0')
        (d / 'results' / 'results.json').write_text(json.dumps([{'task_id':task,'status':'success','score':1.0}]))
        seal(d); return d

    def change(self, name, content):
        d = self.root / 'task-061'; (d / name).write_text(content); seal(d); return d

    def test_exact18_success(self):
        out = aggregate(self.root, 'test-sha')
        self.assertEqual(out['binary_successes'], 18)
        self.assertEqual(out['status'], 'OFFICIAL18_SCORES_PASS')

    def test_zero_score_never_green(self):
        self.change('results/tasks/061/result.txt','0')
        self.change('results/results.json',json.dumps([{'task_id':'061','status':'success','score':0}]))
        with self.assertRaisesRegex(ValueError,'OFFICIAL_SCORE_GATE'): aggregate(self.root,'test-sha')

    def test_nonfinite_out_of_range_and_summary_divergence(self):
        for score in ('nan','inf','1.1','0.5'):
            d = self.change('results/tasks/061/result.txt',score)
            with self.assertRaises(ValueError): audit_task(d,'061','test-sha')

    def test_wrong_candidate_and_evaluator_change(self):
        d = self.change('candidate-sha.txt','old-sha')
        with self.assertRaisesRegex(ValueError,'SHA_MISMATCH'): audit_task(d,'061','test-sha')
        self.change('candidate-sha.txt','test-sha')
        d = self.change('evaluator-integrity.json',json.dumps({'task.py':{'before':'hash','after':'changed'}}))
        with self.assertRaisesRegex(ValueError,'EVALUATOR_MODIFIED'): audit_task(d,'061','test-sha')

    def test_checksum_and_coverage(self):
        d = self.root / 'task-061'; (d / 'osworld.log').write_text('changed')
        with self.assertRaisesRegex(ValueError,'CHECKSUM_MISMATCH'): audit_task(d,'061','test-sha')
        seal(d); (d / 'late-file').write_text('unsealed')
        with self.assertRaisesRegex(ValueError,'CHECKSUM_COVERAGE'): audit_task(d,'061','test-sha')

    def test_cost_fatal_and_missing_action(self):
        for event in ({'http':200,'mandatory_cost_usd':1,'paid_fallback_used':True},
                      {'status':'TERMINAL_FAIL','reason':'ENDPOINT_AUTH_OR_VERSION'},
                      {'status':'WAIT_PROVIDER_CAPACITY'}):
            d = self.change('shim.jsonl', json.dumps({'commit':'test-sha','task_id':'061',**event}))
            with self.assertRaises(ValueError): audit_task(d,'061','test-sha')

    def test_061_evaluator_fallback_cannot_fake_agent_output(self):
        d=self.change('osworld.log','found_edited_photo=0 (path=None)\nAfter GIMP export: edited_photo=cache/061/IMG_7318_edited.jpg')
        with self.assertRaisesRegex(ValueError,'AGENT_OUTPUT_PROVENANCE_UNPROVEN'):
            audit_task(d,'061','test-sha')

    def test_missing_task_and_extra_task(self):
        (self.root / 'task-061' / 'task-id.txt').unlink()
        with self.assertRaisesRegex(ValueError,'TASK_SET'): aggregate(self.root,'test-sha')
        self.fixture('999')
        with self.assertRaisesRegex(ValueError,'TASK_SET'): aggregate(self.root,'test-sha')

    def test_focal_can_never_be18(self):
        focal = self.root / 'focal'; focal.mkdir()
        import shutil
        shutil.copytree(self.root / 'task-061', focal / 'task-061')
        out = aggregate(focal,'test-sha',True)
        self.assertEqual(out['status'],'FOCAL_061_PASS')
        self.assertEqual(out['official_tasks'],1)
        with self.assertRaisesRegex(ValueError,'TASK_SET'): aggregate(focal,'test-sha')

    def test_specialist_action_counts_as_real_agent_action(self):
        d=self.change('shim.jsonl',json.dumps({'commit':'test-sha','task_id':'061',
            'status':'GIMP_SPECIALIST_ACTION_ISSUED'}))
        row=audit_task(d,'061','test-sha')
        self.assertEqual(row['score'],1.0)


if __name__ == '__main__': unittest.main()
