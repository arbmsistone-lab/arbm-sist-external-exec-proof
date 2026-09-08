import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parent

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/file)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

mc=load('mc','arbm-mission-control.py')
ci=load('ci','arbm-context-isolation.py')

class Tests(unittest.TestCase):
    def mission(self):
        return {'id':'m1','status':'RUNNING','control_owner':'ops','lease_owner':'runner-a','checkpoint':'cp-9'}

    def test_cancel_releases_lease(self):
        r=mc.apply_control(self.mission(),'CANCEL','ops')
        self.assertEqual(r['status'],'CANCELLED'); self.assertIsNone(r['lease_owner'])

    def test_preempt_and_resume(self):
        r=mc.apply_control(self.mission(),'PREEMPT','ops')
        self.assertEqual(r['status'],'PREEMPTED'); self.assertEqual(r['resume_from'],'cp-9')
        q=mc.apply_control(r,'RESUME','ops'); self.assertEqual(q['status'],'QUEUED')

    def test_wrong_owner_blocked(self):
        with self.assertRaises(PermissionError): mc.apply_control(self.mission(),'CANCEL','other')

    def test_namespace_blocks_cross_mission_path(self):
        self.assertTrue(ci.authorize_path('m1','missions/m1/output.json'))
        self.assertFalse(ci.authorize_path('m1','missions/m2/output.json'))
        self.assertFalse(ci.authorize_path('m1','../missions/m1/output.json'))

    def test_secret_namespace_isolated(self):
        self.assertTrue(ci.authorize_secret('m1','mission/m1/provider-key'))
        self.assertFalse(ci.authorize_secret('m1','mission/m2/provider-key'))

    def test_assert_isolated_fail_closed(self):
        with self.assertRaises(PermissionError):
            ci.assert_isolated('m1',['missions/m2/leak.txt'],['mission/m1/ok'])

if __name__=='__main__':
    unittest.main()
