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
        reviews = []
        for role in sorted(bundle.EXPECTED_ROLES):
            reviews.append({
                'role': role,
                'verdict': {
                    'verdict': 'PASS_FIX',
                    'veto': False,
                    'root_cause_class': 'STATE_OR_EXECUTION',
                },
            })
        return {
            'status': 'SWARM_ACCEPTED', 'candidate_sha': sha,
            'zero_spend_mode': 'HARD', 'paid_fallback_used': False,
            'heavy_local': 0, 'robots_total': 10, 'valid_reviews': 10,
            'vetoes': [], 'reviews': reviews,
        }

    def test_specialist_requires_exact_sha_quorum_and_roles(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 's.json'
            p.write_text(json.dumps(self.specialist('a' * 40)))
            self.assertEqual(bundle._validate_specialist(p, 'a' * 40)['valid_reviews'], 10)
            bad = self.specialist('a' * 40); bad['valid_reviews'] = 9
            p.write_text(json.dumps(bad))
            with self.assertRaises(RuntimeError): bundle._validate_specialist(p, 'a' * 40)
            bad = self.specialist('a' * 40); bad['reviews'] = bad['reviews'][:-1]
            p.write_text(json.dumps(bad))
            with self.assertRaises(RuntimeError): bundle._validate_specialist(p, 'a' * 40)
            p.write_text(json.dumps(self.specialist('b' * 40)))
            with self.assertRaises(RuntimeError): bundle._validate_specialist(p, 'a' * 40)

    def test_specialist_rejects_veto_policy_and_unknown_class(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 's.json'
            data = self.specialist('a' * 40); data['vetoes'] = ['state_machine']
            p.write_text(json.dumps(data))
            with self.assertRaises(RuntimeError): bundle._validate_specialist(p, 'a' * 40)
            data = self.specialist('a' * 40); data['paid_fallback_used'] = True
            p.write_text(json.dumps(data))
            with self.assertRaises(RuntimeError): bundle._validate_specialist(p, 'a' * 40)
            data = self.specialist('a' * 40); data['reviews'][0]['verdict']['root_cause_class'] = 'UNKNOWN'
            p.write_text(json.dumps(data))
            with self.assertRaises(RuntimeError): bundle._validate_specialist(p, 'a' * 40)

    def test_hash_tree_hashes_empty_auxiliary_files(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'empty.txt'; p.write_bytes(b'')
            rows = bundle._hash_tree(d)
            self.assertEqual(rows[0]['bytes'], 0)
            self.assertEqual(rows[0]['sha256'], 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855')

    def test_required_file_still_rejects_empty_core_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'core.json'; p.write_bytes(b'')
            with self.assertRaises(RuntimeError): bundle._required_file(p)

    def test_lane_receipt_binds_sha_policy_outcome_and_time(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / 'r.json'
            receipt = {
                'lane': 'fast', 'candidate_sha': 'a' * 40,
                'exit_code': 1, 'timed_out': False, 'success': False,
                'started_epoch': 100, 'finished_epoch': 105, 'elapsed_seconds': 5,
                'zero_spend_mode': 'HARD', 'paid_fallback_used': False, 'heavy_local': 0,
            }
            p.write_text(json.dumps(receipt))
            self.assertFalse(bundle._validate_lane_receipt(p, 'fast', 'a' * 40, False)['success'])
            receipt['success'] = True
            p.write_text(json.dumps(receipt))
            with self.assertRaises(RuntimeError): bundle._validate_lane_receipt(p, 'fast', 'a' * 40, False)

    def test_export_hash_must_match_payload(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            gimp = root / 'current-probe-evidence' / 'gimp'
            gimp.mkdir(parents=True)
            payload = gimp / 'exported-output.bytes'; payload.write_bytes(b'abc')
            digest = gimp / 'exported-output.sha256'
            digest.write_text('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad  exported-output.bytes\n')
            old = os.getcwd(); os.chdir(root)
            try:
                self.assertEqual(bundle._validate_export_hash(), 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
                digest.write_text('0' * 64 + '  exported-output.bytes\n')
                with self.assertRaises(RuntimeError): bundle._validate_export_hash()
            finally:
                os.chdir(old)

    def test_bundle_source_requires_strict_bindings(self):
        source = pathlib.Path(bundle.__file__).read_text(encoding='utf-8')
        self.assertIn("audit3d.get('passed') != 60", source)
        self.assertIn("champion.get('status') != 'PASS'", source)
        self.assertIn("APPROVED_FOCAL_EVIDENCE_BIND_REQUIRED", source)
        self.assertIn("DIAGNOSTIC_EXECUTION_PARITY_REQUIRED", source)
        self.assertIn("ACCEPTED_SPECIALIST_LANE_REQUIRED", source)
        self.assertIn("'paid_fallback_used': False", source)
        self.assertIn("'heavy_local': 0", source)


if __name__ == '__main__':
    unittest.main()
