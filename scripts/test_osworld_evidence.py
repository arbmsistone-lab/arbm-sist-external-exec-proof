import unittest,tempfile,json
from pathlib import Path
from osworld_evidence import seal,verify,aggregate
class EvidenceTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
  for i in ('001','002','003'):
   d=self.root/i;d.mkdir();r=d/'results'/'tasks'/i;r.mkdir(parents=True)
   vals={'candidate-sha.txt':'abc','zero-spend-mode.txt':'HARD','osworld-agent-version.txt':'v13','task-id.txt':i,'task-rc.txt':'0','osworld.log':'official evaluator','endpoint-manifest.json':json.dumps({'agent_build':'b'}),'provider-telemetry.jsonl':json.dumps({'http':200,'agent_build':'b','mandatory_cost_usd':0,'paid_fallback_used':False,'model':'m','provider_attempts':[{'model':'m','status':200,'zero_spend_confirmed':True}]})+'\n'}
   for k,v in vals.items():(d/k).write_text(v)
   (r/'result.txt').write_text('0.5');(d/'results'/'results.json').write_text(json.dumps([{'task_id':i,'status':'success','score':.5}]))
   seal(d)
 def test_valid_evidence(self):self.assertEqual(aggregate(self.root)['aggregate'],'SUCCESS')
 def test_changed_checksum(self):
  (self.root/'001'/'task-rc.txt').write_text('7')
  with self.assertRaisesRegex(ValueError,'CHECKSUM_MISMATCH'):aggregate(self.root)
 def test_missing_checksum_coverage(self):
  (self.root/'001'/'late.txt').write_text('late')
  with self.assertRaisesRegex(ValueError,'CHECKSUM_COVERAGE'):aggregate(self.root)
 def test_task_rc(self):
  d=self.root/'001';(d/'task-rc.txt').write_text('124');seal(d)
  with self.assertRaisesRegex(ValueError,'TASK_RC'):aggregate(self.root)
 def test_evaluator_mismatch(self):
  d=self.root/'001';(d/'results'/'tasks'/'001'/'result.txt').write_text('1');seal(d)
  with self.assertRaisesRegex(ValueError,'EVALUATOR_SUMMARY_MISMATCH'):aggregate(self.root)
 def test_nan_score(self):
  d=self.root/'001';(d/'results'/'tasks'/'001'/'result.txt').write_text('nan');seal(d)
  with self.assertRaisesRegex(ValueError,'INVALID_SCORE'):aggregate(self.root)
 def test_zero_scores(self):
  for d in self.root.iterdir():
   (d/'results'/'tasks'/d.name/'result.txt').write_text('0');(d/'results'/'results.json').write_text(json.dumps([{'task_id':d.name,'status':'success','score':0}]))
   seal(d)
  with self.assertRaisesRegex(ValueError,'ZERO_SCORE'):aggregate(self.root)
 def test_missing_free_proof(self):
  d=self.root/'001';p=d/'provider-telemetry.jsonl';x=json.loads(p.read_text());x['provider_attempts']=[];p.write_text(json.dumps(x));seal(d)
  with self.assertRaisesRegex(ValueError,'FREE_PROVIDER_UNPROVEN'):aggregate(self.root)
if __name__=='__main__':unittest.main()
