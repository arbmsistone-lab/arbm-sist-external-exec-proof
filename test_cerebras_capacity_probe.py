import io,json,os,unittest
from unittest.mock import patch
import cerebras_capacity_probe as c
class T(unittest.TestCase):
 def test_missing_key_zero(self):
  with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD'},clear=True),patch('sys.stdout',new_callable=io.StringIO) as out: self.assertEqual(c.main(),0)
  x=json.loads(out.getvalue()); self.assertEqual(x['status'],'NOT_CONFIGURED'); self.assertEqual(x['certified_tokens_per_day'],0)
 def test_configured_trial_never_certifies(self):
  with patch.dict(os.environ,{'ZERO_SPEND_MODE':'HARD','CEREBRAS_API_KEY':'dummy'},clear=True),patch('sys.stdout',new_callable=io.StringIO) as out: self.assertEqual(c.main(),0)
  x=json.loads(out.getvalue()); self.assertEqual(x['status'],'REJECT_TEMPORARY_TRIAL_NOT_RECURRING'); self.assertFalse(x['recurring_free']); self.assertEqual(x['certified_tokens_per_day'],0)
if __name__=='__main__': unittest.main()