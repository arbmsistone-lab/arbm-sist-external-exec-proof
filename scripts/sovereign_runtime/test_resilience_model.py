#!/usr/bin/env python3
import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from resilience_model import Route,Mission,independent_domains,survives

class ResilienceTests(unittest.TestCase):
 def test_fencing_blocks_stale_executor(self):
  m=Mission("m","a",10); t=m.takeover("b",11)
  with self.assertRaisesRegex(RuntimeError,"STALE_FENCE"): m.checkpoint_write("a",1,1)
  m.checkpoint_write("b",t,1); self.assertEqual(m.checkpoint,1)
 def test_ttl_removes_stale_route(self):
  self.assertFalse(Route("r","c","d",witness_epoch=0,witness_ttl=5).counts(10))
 def test_shared_dependency_collapses_domains(self):
  rs=[Route("a","c","A",{"g"},witness_epoch=10),Route("b","c","B",{"g"},witness_epoch=10)]
  self.assertEqual(independent_domains(rs,"c",10),1)
 def test_two_domain_loss_leaves_three(self):
  rs=[Route(str(i),"c",str(i),witness_epoch=10) for i in range(5)]
  self.assertTrue(survives(rs,"c",10,{"0","1"},3))
 def test_reconciliation_is_logically_exactly_once(self):
  m=Mission("m","a",10)
  self.assertFalse(m.reconcile_effect("k","tx"))
  self.assertTrue(m.reconcile_effect("k","tx"))
  with self.assertRaisesRegex(RuntimeError,"IDEMPOTENCY_CONFLICT"): m.reconcile_effect("k","other")
 def test_active_lease_blocks_takeover(self):
  m=Mission("m","a",10)
  with self.assertRaisesRegex(RuntimeError,"LEASE_ACTIVE"): m.takeover("b",10)

if __name__=="__main__": unittest.main()
