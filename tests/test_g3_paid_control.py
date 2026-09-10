import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import types as stdtypes
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'certification' / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sys.modules.setdefault('mm_agents', stdtypes.ModuleType('mm_agents'))
control = load('mm_agents.g3_paid_control', 'g3_paid_control.py')
load('mm_agents.gemini_action_parser', 'vendor-gemini-action-parser.py')
load('mm_agents.gemini_agent', 'vendor-gemini-agent.py')
adapter = load('g3_paid_adapter', 'g3-gemini-fc-adapter.py')
from google.genai import types  # noqa: E402


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {
            'authorized_total_usd': '5.00', 'reconciliation_status': 'COMPLETE',
            'provider_credit_status': 'AVAILABLE', 'reconciled_total_usd': '4.00',
            'per_call_cost_bound_status': 'PROVEN',
            'reserved_run_usd': '0.50', 'accounted_run_ids': ['1'],
            'audit_3x': dict.fromkeys('ABC', 'PASS'),
            'audited_files_sha256': {
                name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in ('certification/g3_paid_control.py',
                             'certification/g3-gemini-fc-adapter.py',
                             '.github/workflows/osworld-g3-paid-smoke-v2.yml',
                             '.github/workflows/osworld-g3-paid-model-probe.yml')
            },
        }
        self.kwargs = dict(repository=control.REPOSITORY, branch=control.BRANCH,
                           attempt='1', run_id='2', candidate_sha='candidate', root=ROOT,
                           history=[{'databaseId': 1, 'headSha': 'previous', 'status': 'completed',
                                     'workflowName': 'G3 paid smoke'},
                                    {'databaseId': 2, 'headSha': 'candidate', 'status': 'in_progress',
                                     'workflowName': 'G3 paid smoke'}])

    def test_valid_fully_reconciled_reservation(self):
        self.assertEqual(control.admit(self.ledger, **self.kwargs)['state'], 'ADMITTED')

    def test_budget_edge_and_nonfinite_values(self):
        for spent, reserve in [('4.51', '0.5'), ('NaN', '.1'), ('Infinity', '.1'), ('-1', '.1'), ('1', '0')]:
            with self.subTest(spent=spent, reserve=reserve):
                self.ledger.update(reconciled_total_usd=spent, reserved_run_usd=reserve)
                with self.assertRaises(control.PaidGateError):
                    control.admit(self.ledger, **self.kwargs)

    def test_unknown_cost_missing_credit_and_all_three_audits(self):
        variants = [dict(reconciliation_status='INCOMPLETE'), dict(provider_credit_status='DEPLETED'),
                    dict(per_call_cost_bound_status='UNPROVEN'),
                    dict(reconciled_total_usd=None), dict(authorized_total_usd='6'),
                    dict(audit_3x={'A': 'PASS', 'B': 'PASS', 'C': 'BLOCKED'})]
        for variant in variants:
            with self.subTest(variant=variant), self.assertRaises(control.PaidGateError):
                control.admit({**self.ledger, **variant}, **self.kwargs)

    def test_wrong_repository_branch_and_rerun_are_rejected(self):
        for override in [dict(repository='another/repo'), dict(branch='master'), dict(attempt='2')]:
            with self.subTest(override=override), self.assertRaises(control.PaidGateError):
                control.admit(self.ledger, **{**self.kwargs, **override})

    def test_unaccounted_or_concurrent_run_and_reused_sha(self):
        for override in [dict(databaseId=3), dict(status='in_progress'), dict(headSha='candidate')]:
            kwargs = copy.deepcopy(self.kwargs)
            kwargs['history'][0].update(override)
            with self.subTest(override=override), self.assertRaises(control.PaidGateError):
                control.admit(self.ledger, **kwargs)

    def test_missing_current_or_truncated_history(self):
        for history in [[], [self.kwargs['history'][0]], self.kwargs['history'] * 500]:
            with self.assertRaises(control.PaidGateError):
                control.admit(self.ledger, **{**self.kwargs, 'history': history})

    def test_hash_tamper(self):
        self.ledger['audited_files_sha256']['certification/g3_paid_control.py'] = '0' * 64
        with self.assertRaisesRegex(control.PaidGateError, 'HASH_MISMATCH'):
            control.admit(self.ledger, **self.kwargs)

    def test_official_full_pass_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'result.txt'
            for value in ['', '0', '0.5', 'nan', 'inf', '-1', '2', 'not-a-score']:
                path.write_text(value)
                with self.subTest(value=value), self.assertRaises(control.PaidGateError):
                    control.official_result(path)
            path.write_text('1.0\n')
            self.assertEqual(control.official_result(path), 1.0)

    def test_checked_in_ledger_blocks_without_network_or_vm(self):
        ledger = json.loads((ROOT / 'certification/g3-paid-budget.json').read_text())
        with self.assertRaisesRegex(control.PaidGateError, 'UNRECONCILED'):
            control.admit(ledger, **self.kwargs)


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.journal = Path(self.temp.name) / 'usage.jsonl'
        env = patch.dict(os.environ, {'ARBM_G3_USAGE_LOG': str(self.journal),
                                     'ARBM_G3_TASK_COST_CAP_USD': '0.50'})
        env.start()
        self.addCleanup(env.stop)
        self.client = Mock()
        self.client.models.generate_content.return_value = stdtypes.SimpleNamespace(
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=1000, candidates_token_count=20,
                thoughts_token_count=10, total_token_count=1030))
        self.agent = adapter.CappedGeminiFCAgent(client=self.client, model_id='gemini-3.5-flash',
                                                action_space='pyautogui', max_tokens=2048)

    def rows(self):
        return [json.loads(line) for line in self.journal.read_text().splitlines()]

    def test_credit_depletion_one_attempt_no_sleep_no_secret(self):
        secret = 'synthetic-secret-must-never-be-logged'
        self.client.models.generate_content.side_effect = RuntimeError(
            '429 RESOURCE_EXHAUSTED Your prepayment credits are depleted ' + secret)
        with patch('time.sleep') as sleep:
            with self.assertRaisesRegex(RuntimeError, 'PROVIDER_CREDIT_DEPLETED'):
                self.agent._call_model()
            self.agent.reset()
            with self.assertRaisesRegex(RuntimeError, 'PROVIDER_CREDIT_DEPLETED'):
                self.agent._call_model()
            sleep.assert_not_called()
        self.client.models.generate_content.assert_called_once()
        self.assertNotIn(secret, self.journal.read_text())
        self.assertIsNone(self.rows()[-1]['call_cost_usd'])
        self.assertEqual(self.rows()[-1]['usage_status'], 'UNKNOWN')

    def test_missing_usage_blocks_continuation(self):
        self.client.models.generate_content.return_value = stdtypes.SimpleNamespace(usage_metadata=None)
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, 'METADATA_INVALID'):
                self.agent._call_model()
        self.client.models.generate_content.assert_called_once()

    def test_spend_survives_reset_task_context_does_not(self):
        self.agent._call_model()
        cost = self.agent._run_cost_usd
        self.agent._instruction = 'Task A private state'
        self.agent.messages = [types.Content(role='user', parts=[types.Part.from_text(text='Task A')])]
        self.agent.reset()
        self.assertEqual(self.agent._run_cost_usd, cost)
        self.assertEqual(self.agent._instruction, '')
        self.assertEqual(self.agent.messages, [])
        self.agent._call_model()
        self.assertAlmostEqual(self.agent._run_cost_usd, 2 * cost)
        self.assertGreaterEqual(self.rows()[-1]['latency_ms'], 0)
        self.assertEqual(self.rows()[-1]['total_tokens'], 1030)

    def test_journal_must_exist_before_request(self):
        with patch.dict(os.environ, {'ARBM_G3_USAGE_LOG': ''}):
            with self.assertRaisesRegex(RuntimeError, 'JOURNAL_REQUIRED'):
                self.agent._call_model()
        self.client.models.generate_content.assert_not_called()

    def test_compaction_preserves_function_pairs_and_signatures(self):
        self.agent._instruction = 'Original public instruction'
        self.agent.messages = [types.Content(role='user', parts=[types.Part.from_text(text='initial')])]
        for i in range(60):
            self.agent.messages.extend([
                types.Content(role='model', parts=[types.Part(
                    function_call=types.FunctionCall(name='computer_agent_api:click', args={'x': i, 'y': i}),
                    thought_signature=b'original-signature')]),
                types.Content(role='user', parts=[types.Part(function_response=types.FunctionResponse(
                    name='computer_agent_api:click', response={'result': 'observed'}))]),
            ])
            self.agent._compact_context()
            self.assertLessEqual(len(self.agent.messages), 7)
        self.assertIn('Original public instruction', self.agent.messages[0].parts[0].text)
        for message in self.agent.messages[1::2]:
            self.assertEqual(message.role, 'model')
            self.assertEqual(message.parts[0].thought_signature, b'original-signature')

    def test_compaction_with_parse_repair_never_starts_with_orphan_response(self):
        self.agent.messages = [types.Content(role=role, parts=[types.Part.from_text(text='data')])
                               for role in ['user', 'model', 'user', 'model', 'user', 'user', 'model', 'user']]
        self.agent._compact_context()
        self.assertEqual(self.agent.messages[1].role, 'model')

    def test_visual_stall_stops_before_fifth_model_request(self):
        with patch.object(adapter.GeminiFCAgent, 'predict', return_value=('', [])) as predict:
            for _ in range(4):
                self.agent.predict('A public GUI task', {'screenshot': b'same-pixels'})
            with self.assertRaisesRegex(RuntimeError, 'NO_VISUAL_PROGRESS'):
                self.agent.predict('A public GUI task', {'screenshot': b'same-pixels'})
            self.assertEqual(predict.call_count, 4)

    def test_http_retry_and_output_cap_configured_on_wrapper(self):
        with patch.dict(os.environ, {'GEMINI_G3_PAID_CERT_KEY': 'synthetic'}), patch.object(adapter.genai, 'Client') as client:
            wrapped = adapter.ArbmG3Agent()
            options = client.call_args.kwargs['http_options']
            self.assertEqual(options.retry_options.attempts, 1)
            self.assertEqual(options.timeout, 45000)
            self.assertEqual(wrapped._core.max_tokens, 2048)

    def test_reject_shell_install_and_terminal_before_accepting_actions(self):
        for name, args in [('type', {'text': 'python3 -m pip install example'}),
                           ('type', {'text': 'cat << EOF > script.py'}),
                           ('hotkey', {'keys': ['Control_L', 'Alt_L', 't']}),
                           ('wait', {'seconds': 30})]:
            response = types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
                role='model', parts=[types.Part(function_call=types.FunctionCall(
                    name='computer_agent_api:' + name, args=args))]))])
            with self.subTest(name=name), self.assertRaises(adapter.InvalidActionError):
                self.agent._parse_response(response)
            self.assertEqual(self.agent.actions, [])
            self.assertEqual(self.agent.messages, [])

    def test_allow_direct_gui_actions_and_short_wait(self):
        for name, args in [('type', {'text': 'Meeting at 09:00'}),
                           ('hotkey', {'keys': ['ctrl', 's']}),
                           ('click', {'x': 350, 'y': 100}), ('wait', {'seconds': 1})]:
            self.assertIsNone(control.gui_action_violation({'action_type': name, 'parameters': args}))


if __name__ == '__main__':
    unittest.main()
