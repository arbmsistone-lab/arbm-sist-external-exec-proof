import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import osworld_061_performance_swarm as perf
import osworld_061_specialist_swarm as swarm


class PerformanceSwarmTests(unittest.TestCase):
    def verdict(self, role, root='AGENT_LOGIC', veto=False, verdict='PASS_FIX'):
        return {
            'role': role,
            'verdict': verdict,
            'root_cause_class': root,
            'causal_chain': ['grounded causal finding'],
            'definitive_fix': 'preserve current fix',
            'regression_risks': [],
            'required_proofs': [],
            'confidence': 0.9,
            'veto': veto,
        }

    def test_workers_are_strictly_bounded(self):
        with mock.patch.dict(os.environ, {'ARBM_SWARM_REMOTE_WORKERS': '99'}):
            self.assertEqual(perf._bounded_workers(), 4)
        with mock.patch.dict(os.environ, {'ARBM_SWARM_REMOTE_WORKERS': '0'}):
            self.assertEqual(perf._bounded_workers(), 1)
        with mock.patch.dict(os.environ, {'ARBM_SWARM_REMOTE_WORKERS': 'bad'}):
            self.assertEqual(perf._bounded_workers(), 3)

    def test_remote_worker_never_uses_local_provider(self):
        source = pathlib.Path(perf.__file__).read_text(encoding='utf-8')
        body = source[source.index('def _remote_robot'):source.index('def _skipped_robot')]
        self.assertNotIn('local_text_review(', body)
        self.assertNotIn('LOCAL_VLM_ROUTE.call', body)
        self.assertIn("('openrouter', free_route, 140)", body)
        self.assertIn("('groq', groq_route, 120)", body)

    def test_quorum_contract_remains_ten_roles(self):
        self.assertEqual(len(swarm.ROLES), 10)
        self.assertEqual(len({name for name, _ in swarm.ROLES}), 10)

    def test_fast_path_short_circuits_after_unusable_warmup(self):
        bad = {'role': swarm.ROLES[0][0], 'specialty': swarm.ROLES[0][1],
               'provider': None, 'verdict': None, 'attempts': [], 'raw_outputs': []}
        with mock.patch.object(perf, '_remote_robot', return_value=bad):
            robots = perf._run_remote_robots('e', 'c', None, 'p')
        self.assertEqual(len(robots), 10)
        self.assertIsNone(robots[0]['verdict'])
        self.assertTrue(all(r['attempts'][0]['status'] == 'short_circuited_after_warmup_failure'
                            for r in robots[1:]))

    def test_unknown_or_veto_cannot_be_accepted_by_contract(self):
        good = [self.verdict(name) for name, _ in swarm.ROLES]
        self.assertTrue(all(swarm.valid_verdict(v, v['role']) for v in good))
        unknown = self.verdict(swarm.ROLES[0][0], root='UNKNOWN')
        veto = self.verdict(swarm.ROLES[1][0], veto=True, verdict='REJECT_FIX')
        self.assertTrue(swarm.valid_verdict(unknown, unknown['role']))
        self.assertTrue(swarm.valid_verdict(veto, veto['role']))
        classes = {v['root_cause_class'] for v in good[1:] + [unknown]}
        self.assertIn('UNKNOWN', classes)
        self.assertTrue(veto['veto'])


if __name__ == '__main__':
    unittest.main()
