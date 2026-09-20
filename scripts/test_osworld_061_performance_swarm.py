import os
import pathlib
import sys
import unittest
import unittest.mock as mock

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

    def robot(self, role, **kwargs):
        return {'role': role, 'specialty': role, 'provider': 'test',
                'verdict': self.verdict(role, **kwargs), 'attempts': [], 'raw_outputs': []}

    def test_workers_are_strictly_bounded(self):
        with mock.patch.dict(os.environ, {'ARBM_SWARM_REMOTE_WORKERS': '99'}):
            self.assertEqual(perf._bounded_workers(), 4)
        with mock.patch.dict(os.environ, {'ARBM_SWARM_REMOTE_WORKERS': '0'}):
            self.assertEqual(perf._bounded_workers(), 1)
        with mock.patch.dict(os.environ, {'ARBM_SWARM_REMOTE_WORKERS': 'bad'}):
            self.assertEqual(perf._bounded_workers(), 3)

    def test_provider_budgets_are_strictly_bounded(self):
        with mock.patch.dict(os.environ, {
            'ARBM_SWARM_OPENROUTER_BUDGET_S': '999',
            'ARBM_SWARM_GROQ_BUDGET_S': '1',
            'ARBM_SWARM_REPAIR_BUDGET_S': 'bad'}):
            self.assertEqual(perf._budgets(), (90, 10, 20))

    def test_remote_worker_never_uses_local_provider(self):
        source = pathlib.Path(perf.__file__).read_text(encoding='utf-8')
        body = source[source.index('def _remote_robot'):source.index('def _skipped_robot')]
        self.assertNotIn('local_text_review(', body)
        self.assertNotIn('LOCAL_VLM_ROUTE.call', body)
        self.assertIn("('openrouter', free_route, openrouter_budget)", body)
        self.assertIn("('groq', groq_route, groq_budget)", body)

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

    def test_incomplete_quorum_is_fallback_eligible(self):
        robots = [self.robot(name) for name, _ in swarm.ROLES]
        robots[-1]['verdict'] = None
        valid, vetoes, classes, unknown, covered, accepted, fallback = perf._classification(robots)
        self.assertEqual(len(valid), 9)
        self.assertFalse(vetoes)
        self.assertFalse(unknown)
        self.assertFalse(accepted)
        self.assertTrue(fallback)

    def test_substantive_veto_is_never_fallback_eligible(self):
        robots = [self.robot(name) for name, _ in swarm.ROLES]
        robots[1] = self.robot(swarm.ROLES[1][0], veto=True, verdict='REJECT_FIX')
        _, vetoes, _, _, _, accepted, fallback = perf._classification(robots)
        self.assertIn(swarm.ROLES[1][0], vetoes)
        self.assertFalse(accepted)
        self.assertFalse(fallback)

    def test_unknown_is_never_fallback_eligible(self):
        robots = [self.robot(name) for name, _ in swarm.ROLES]
        robots[0] = self.robot(swarm.ROLES[0][0], root='UNKNOWN')
        _, _, classes, unknown, _, accepted, fallback = perf._classification(robots)
        self.assertEqual(classes['UNKNOWN'], 1)
        self.assertEqual(unknown, [swarm.ROLES[0][0]])
        self.assertFalse(accepted)
        self.assertFalse(fallback)

    def test_clean_ten_of_ten_is_accepted_without_fallback(self):
        robots = [self.robot(name) for name, _ in swarm.ROLES]
        valid, vetoes, classes, unknown, covered, accepted, fallback = perf._classification(robots)
        self.assertEqual(len(valid), 10)
        self.assertFalse(vetoes)
        self.assertFalse(unknown)
        self.assertEqual(len(covered), 10)
        self.assertEqual(classes['AGENT_LOGIC'], 10)
        self.assertTrue(accepted)
        self.assertFalse(fallback)


if __name__ == '__main__':
    unittest.main()
