import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import osworld_061_evidence_bundle as bundle


class EvidenceBundleTests(unittest.TestCase):
    def specialist(self, sha):
        return {
            'status': 'SWARM_ACCEPTED', 'candidate_sha': sha,
            'zero_spend_mode': 'HARD', 'paid_fallback_used': False,
            'heavy_local': 0, 'robots_total': 10, 'valid_reviews': 10,
            'vetoes': [],
        }

    def test_specialist_requires_exact_sha_and_quorum(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 's.json'
            p.write_text(json.dumps(self.specialist('a' * 40)))
            self.assertEqual(bundle._validate_specialist(p, 'a' * 40)['valid_reviews'], 10)
            bad = self.specialist('a' * 40); bad['valid_reviews'] = 9
            p.write_text(json.dumps(bad))
            with self.assertRaises(RuntimeError): bundle._validate_specialist(p, 'a' * 40)
            p.write_text(json.dumps(self.specialist('b' * 40)))
            with self.assertRaises(RuntimeError): bundle._validate_specialist(p, 'a' * 40)

    def test_specialist_rejects_veto_and_policy_drift(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 's.json'
            data = self.specialist('a' * 40); data['vetoes'] = ['state_machine']
            p.write_text(json.dumps(data))
            with self.assertRaises(RuntimeError): bundle._validate_specialist(p, 'a' * 40)
            data = self.specialist('a' * 40); data['paid_fallback_used'] = True
            p.write_text(json.dumps(data))
            with self.assertRaises(RuntimeError): bundle._validate_specialist(p, 'a' * 40)

    def test_hash_tree_rejects_empty_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'empty.txt'; p.write_bytes(b'')
            with self.assertRaises(RuntimeError): bundle._hash_tree(d)

    def test_bundle_source_requires_3d_60_of_60(self):
        source = pathlib.Path(bundle.__file__).read_text(encoding='utf-8')
        self.assertIn("audit3d.get('passed') != 60", source)
        self.assertIn("champion.get('status') != 'PASS'", source)
        self.assertIn("if fast_outcome != 'success' and replay_outcome != 'success' and full_outcome != 'success'", source)
        self.assertIn("'paid_fallback_used': False", source)
        self.assertIn("'heavy_local': 0", source)


if __name__ == '__main__':
    unittest.main()
