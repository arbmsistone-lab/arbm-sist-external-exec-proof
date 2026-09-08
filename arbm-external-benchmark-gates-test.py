import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('g',ROOT/'arbm-external-benchmark-gates.py')
g=importlib.util.module_from_spec(spec); spec.loader.exec_module(g)

class Tests(unittest.TestCase):
    def test_terminal_protocol_is_frozen(self):
        cmd=g.terminal_command('arbm.agent:Agent')
        self.assertEqual(cmd[:4],["harbor","run","-d",g.TERMINAL_DATASET])
        self.assertEqual(cmd[-2:],['-k','5'])

    def test_missing_terminal_evidence_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(g.validate_terminal_evidence(Path(d)))

    def test_missing_osworld_evidence_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(g.validate_osworld_evidence(Path(d)))

    def test_only_maintainer_verified_can_certify(self):
        self.assertFalse(g.certified_external({'verified_by_maintainer':False},[]))
        self.assertTrue(g.certified_external({'verified_by_maintainer':True},[]))

if __name__=='__main__': unittest.main()
