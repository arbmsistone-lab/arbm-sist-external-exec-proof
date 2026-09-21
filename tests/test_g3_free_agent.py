import io
import hashlib
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'certification'))
from g3_free_control import journal_report, load_agent, safe_model_path, quota_admission

agent_module = load_agent()


def payload(action='click', **params):
    if action == 'click' and not params:
        params = {'x': 500, 'y': 500}
    return dict(action=action, parameters=params, state_summary='Read the visible labels.',
                target='Center of the visible button.', expected_change='The selected page opens.')


def response(actions=None, model=None, cost=0):
    actions = [payload()] if actions is None else actions
    return {'model': model or agent_module.MODEL, 'provider': 'test-provider',
            'usage': {'cost': cost, 'prompt_tokens': 100, 'completion_tokens': 30, 'total_tokens': 130},
            'choices': [{'finish_reason': 'tool_calls', 'message': {'content': None, 'tool_calls': [
                {'id': f'tool{i}', 'type': 'function', 'function': {'name': 'desktop_action',
                 'arguments': json.dumps(p)}} for i, p in enumerate(actions)]}}]}


class FreeAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.log = Path(self.temp.name) / 'usage.jsonl'
        # Each contract selects its observation mode explicitly. Workflow inputs
        # must not leak into tests for the default mode or another provider.
        self.env = patch.dict(os.environ, {'ARBM_G3_USAGE_LOG': str(self.log),
                                          'ARBM_G3_FREE_MODEL': agent_module.MODEL,
                                          'ARBM_G3_PROVIDER': 'openrouter',
                                          'ARBM_G3_COORDINATE_GRID': '0',
                                          'ARBM_G3_SQUARE_OBSERVATION': '0',
                                          'ARBM_G3_SCREENSHOT_OCR': '0',
                                          'GITHUB_RUN_ID': 'test', 'GITHUB_SHA': 'test-sha'})
        self.env.start()
        self.calls = []
        self.responses = []

        def create(**kwargs):
            self.calls.append(kwargs)
            value = self.responses.pop(0)
            if isinstance(value, BaseException):
                raise value
            return value

        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        self.agent = agent_module.ArbmG3Agent(client=client)
        image = io.BytesIO()
        Image.new('RGB', (1920, 1080), 'white').save(image, format='PNG')
        self.obs = {'screenshot': image.getvalue()}

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def predict(self):
        return self.agent.predict('Complete the task using the GUI.', self.obs)

    def assert_accounted(self, count):
        report = journal_report(self.log)
        self.assertTrue(report['accounting_complete'])
        self.assertEqual(report['started'], count)
        self.assertEqual(report['pending_requests'], 0)
        rows = [json.loads(line) for line in self.log.read_text().splitlines()]
        for row in rows:
            for key in ('run_id', 'SHA', 'task', 'step', 'call_index', 'requested_model',
                        'returned_model', 'latency_ms', 'structural_valid', 'action_status',
                        'screenshot_hash', 'screen_changed', 'retry_count', 'zero_spend', 'terminal_state'):
                self.assertIn(key, row)
        return report

    def test_one_valid_action_and_zero_request_contract(self):
        self.responses = [response()]
        _, commands = self.predict()
        self.assertEqual(commands, ['pyautogui.click(x=960, y=540)'])
        request = self.calls[0]
        self.assertFalse(request['parallel_tool_calls'])
        self.assertEqual(request['tool_choice']['function']['name'], 'desktop_action')
        self.assertLessEqual(request['max_tokens'], 1024)
        self.assertFalse(request['extra_body']['provider']['allow_fallbacks'])
        self.assertEqual(request['extra_body']['provider']['max_price'], {'prompt': 0, 'completion': 0})
        self.assert_accounted(1)

    def test_zero_calls_repaired_same_screenshot_no_action_replay(self):
        self.responses = [response([]), response()]
        _, commands = self.predict()
        self.assertEqual(len(commands), 1)
        self.assertEqual(self.calls[0]['messages'][1]['content'][1], self.calls[1]['messages'][1]['content'][1])
        self.assertIn('EXACTLY_ONE_TOOL_REQUIRED', self.calls[1]['messages'][1]['content'][0]['text'])
        self.assertEqual(self.assert_accounted(2)['structural_rejections'], 1)

    def test_multiple_calls_bounded_and_never_issued(self):
        self.responses = [response([payload(), payload()])] * 3
        with self.assertRaisesRegex(RuntimeError, 'STRUCTURAL_RETRY_EXHAUSTED'):
            self.predict()
        self.assertEqual(len(self.agent._history), 0)
        self.assertEqual(self.assert_accounted(3)['structural_rejections'], 3)

    def test_invalid_parameters(self):
        self.responses = [response([payload('click', text='bad')]), response()]
        self.predict()
        self.assert_accounted(2)

    def test_invalid_coordinates(self):
        for value in (-1, 1001, True, '500', float('nan')):
            with self.subTest(value=value), self.assertRaises(agent_module.StructuralError):
                agent_module.validate_action(payload('click', x=value, y=500))

    def test_empty_response(self):
        self.responses = [None] * 3
        with self.assertRaisesRegex(RuntimeError, 'STRUCTURAL_RETRY_EXHAUSTED'):
            self.predict()
        self.assert_accounted(3)

    def test_timeout_is_terminal_no_retry_and_survives_reset(self):
        self.responses = [TimeoutError('sensitive-text')]
        with self.assertRaisesRegex(RuntimeError, 'PROVIDER_TIMEOUT'):
            self.predict()
        self.agent.reset()
        with self.assertRaisesRegex(RuntimeError, 'PROVIDER_TIMEOUT'):
            self.predict()
        self.assertEqual(len(self.calls), 1)
        self.assertNotIn('sensitive-text', self.log.read_text())
        self.assert_accounted(1)

    def test_wall_timeout_does_not_wait_for_worker(self):
        def slow(**kwargs):
            time.sleep(0.15)
            return response()
        self.agent.client.chat.completions.create = slow
        self.agent.timeout = 0.01
        with self.assertRaisesRegex(RuntimeError, 'PROVIDER_TIMEOUT'):
            self.predict()
        self.assert_accounted(1)

    def test_429(self):
        error = RuntimeError('private body')
        error.status_code = 429
        self.responses = [error]
        with self.assertRaisesRegex(RuntimeError, 'PROVIDER_RATE_LIMITED'):
            self.predict()
        self.assert_accounted(1)

    def test_provider_failure(self):
        self.responses = [ConnectionError('private provider details')]
        with self.assertRaisesRegex(RuntimeError, 'PROVIDER_FAILURE'):
            self.predict()
        self.assert_accounted(1)

    def test_returned_model_mismatch(self):
        self.responses = [response(model='unapproved/model')]
        with self.assertRaisesRegex(RuntimeError, 'MODEL_IDENTITY_MISMATCH'):
            self.predict()
        self.assertEqual(len(self.agent._history), 0)
        self.assert_accounted(1)

    def test_loop_rejected_before_action(self):
        self.responses = [response(), response(), response([payload('press_key', key='tab')])]
        self.predict()
        _, commands = self.predict()
        self.assertEqual(commands, ["pyautogui.press('tab')"])
        self.assertEqual(self.assert_accounted(3)['structural_rejections'], 1)

    def test_unchanged_screen_gate(self):
        self.responses = [response([payload('press_key', key=k)]) for k in ('a', 'b', 'c', 'd', 'e')]
        for _ in range(5):
            self.predict()
        with self.assertRaisesRegex(RuntimeError, 'NO_VISUAL_PROGRESS'):
            self.predict()
        self.assert_accounted(5)

    def test_done(self):
        self.responses = [response([payload('done')])]
        self.assertEqual(self.predict()[1], ['DONE'])
        with self.assertRaisesRegex(RuntimeError, 'ALREADY_TERMINAL'):
            self.predict()
        self.assert_accounted(1)

    def test_infeasible(self):
        self.responses = [response([payload('infeasible')])]
        self.assertEqual(self.predict()[1], ['FAIL'])
        self.assert_accounted(1)

    def test_nonzero_and_missing_cost_fail_closed(self):
        for cost in (0.01, None, -1, 'NaN'):
            with self.subTest(cost=cost):
                self.agent._terminal_error = None
                self.responses = [response(cost=cost)]
                with self.assertRaisesRegex(RuntimeError, 'COST'):
                    self.predict()
        self.assert_accounted(4)

    def test_terminal_shell_and_invalid_keys_blocked(self):
        for item in (payload('hotkey', keys=['ctrl', 'alt', 't']),
                     payload('hotkey', keys=['alt', 'f2']),
                     payload('press_key', key='win'), payload('type', text='pip install x'),
                     payload('type', text='javascript:alert(1)'), payload('wait', seconds=9)):
            with self.subTest(item=item), self.assertRaises(agent_module.StructuralError):
                agent_module.validate_action(item)

    def test_process_interruption_reconciled_once(self):
        self.responses = [response()]
        self.predict()
        rows = self.log.read_text().splitlines()
        self.log.write_text(rows[0] + '\n')
        self.assertTrue(journal_report(self.log, True)['accounting_complete'])
        size = self.log.stat().st_size
        self.assertTrue(journal_report(self.log, True)['accounting_complete'])
        self.assertEqual(self.log.stat().st_size, size)
        self.assertFalse(journal_report(self.log)['all_calls_observed_zero_cost'])

    def test_safe_physical_path_preserves_model_identity(self):
        self.assertEqual(safe_model_path(agent_module.MODEL), 'dots-studio__dots-3-note-preview__free')

    def test_context_bounded(self):
        self.responses = [response()]
        self.predict()
        self.assertEqual(len(self.agent._messages_for(self.obs['screenshot'], None)), 2)
        self.assertEqual(self.agent._history.maxlen, 6)

    def test_action_intent_mismatch_rejected(self):
        action = payload('type', text='Inbox')
        action['expected_change'] = 'Click on the Inbox tab.'
        with self.assertRaisesRegex(agent_module.StructuralError, 'ACTION_INTENT_MISMATCH'):
            agent_module.validate_action(action)

    def test_quota_metadata_sanitized(self):
        error = RuntimeError('secret must never be logged')
        error.status_code = 429
        error.body = {'message': 'Rate limit exceeded: free-models-per-day'}
        error.response = SimpleNamespace(headers={'x-ratelimit-reset': '1790000000000',
                                                  'authorization': 'private-token'})
        details = agent_module.provider_error_details(error)
        self.assertEqual(details['quota_scope'], 'FREE_REQUESTS_PER_DAY')
        self.assertNotIn('private-token', json.dumps(details))
        self.assertEqual(details['quota_headers']['x-ratelimit-reset'], '1790000000000')

    def test_ocr_is_host_only_bounded_and_grounded(self):
        tsv = 'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n'
        tsv += '5\t1\t1\t1\t1\t1\t180\t100\t40\t20\t95\tCancel\n'
        with patch.dict(os.environ, {'ARBM_G3_SCREENSHOT_OCR': '1'}), patch.object(agent_module.subprocess, 'run') as run:
            run.return_value = SimpleNamespace(stdout=tsv)
            out = agent_module.screenshot_ocr(self.obs['screenshot'], 400, 240)
        self.assertEqual(out['labels'][0], {'text': 'Cancel', 'x': 500, 'y': 458})
        self.assertEqual(run.call_args.args[0][0], 'tesseract')
        self.assertNotIn('shell', run.call_args.kwargs)

    def test_known_daily_quota_blocks_until_provider_reset(self):
        root = Path(self.temp.name)
        proof = {'http_status': 429, 'quota_scope': 'FREE_REQUESTS_PER_DAY',
                 'quota_headers': {'x-ratelimit-remaining': '0', 'x-ratelimit-reset': '2000'}}
        receipt = root / 'receipt.json'
        receipt.write_text(json.dumps(proof))
        lock = {'receipt_path': 'receipt.json', 'receipt_sha256': hashlib.sha256(receipt.read_bytes()).hexdigest(),
                'not_before_unix_ms': 2000, 'reset_utc': 'provider-reset'}
        (root / 'g3-free-quota-lock.json').write_text(json.dumps(lock))
        with self.assertRaisesRegex(RuntimeError, 'DAILY_QUOTA_BLOCKED'):
            quota_admission(root, 1999)
        quota_admission(root, 2000)
        receipt.write_text('{}')
        with self.assertRaisesRegex(RuntimeError, 'PROOF_INVALID'):
            quota_admission(root, 1999)

    def test_no_calls_is_not_missing_usage_or_model_proof(self):
        report = journal_report(self.log)
        self.assertTrue(report['accounting_complete'])
        self.assertEqual(report['journal_state'], 'NO_REQUESTS_STARTED')
        self.assertFalse(report['all_calls_observed_zero_cost'])


    def test_groq_transport_isolated_from_openrouter_parameters(self):
        client = self.agent.client
        self.responses = [response(model='qwen/qwen3.8-27b')]
        with patch.dict(os.environ, {'ARBM_G3_PROVIDER': 'groq',
                                     'ARBM_G3_FREE_MODEL': 'qwen/qwen3.8-27b'}):
            agent = agent_module.ArbmG3Agent(client=client)
            agent.predict('Complete the task using the GUI.', self.obs)
        request = self.calls[-1]
        self.assertNotIn('extra_body', request)
        self.assertEqual(request['reasoning_effort'], 'none')
        self.assertEqual(request['model'], 'qwen/qwen3.8-27b')
        rows = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(rows[-1]['provider_gateway'], 'groq')

    def test_groq_flag_cannot_admit_live_client(self):
        with patch.dict(os.environ, {'ARBM_G3_PROVIDER': 'groq',
                                     'ARBM_G3_FREE_MODEL': 'qwen/qwen3.8-27b',
                                     'ARBM_G3_GROQ_FREE_PLAN_PROVEN': '1'}):
            with self.assertRaisesRegex(RuntimeError, 'ACCOUNT_PROOF_REQUIRED'):
                agent_module.ArbmG3Agent()

    def test_groq_missing_cost_cannot_be_recorded_as_reported_zero(self):
        with patch.dict(os.environ, {'ARBM_G3_PROVIDER': 'groq',
                                     'ARBM_G3_FREE_MODEL': 'qwen/qwen3.8-27b',
                                     'ARBM_G3_GROQ_FREE_PLAN_PROVEN': '1'}):
            agent = agent_module.ArbmG3Agent(client=self.agent.client)
            self.responses = [response(model='qwen/qwen3.8-27b', cost=None)]
            with self.assertRaisesRegex(RuntimeError, 'COST_NOT_PROVEN'):
                agent.predict('Synthetic GUI test.', self.obs)
        terminal = json.loads(self.log.read_text().splitlines()[-1])
        self.assertIsNot(terminal['zero_spend'], True)
        self.assertIsNone(terminal.get('reported_cost_usd'))

    def test_wrong_provider_model_pair_rejected_before_network(self):
        for provider, model in [('openrouter', 'qwen/qwen3.8-27b'), ('groq', agent_module.MODEL)]:
            with patch.dict(os.environ, {'ARBM_G3_PROVIDER': provider, 'ARBM_G3_FREE_MODEL': model}):
                with self.assertRaisesRegex(RuntimeError, 'MODEL_PROVIDER_MISMATCH'):
                    agent_module.ArbmG3Agent(client=self.agent.client)

    def test_grid_preserves_original_geometry_and_bytes(self):
        before = bytes(self.obs['screenshot'])
        transformed = agent_module.coordinate_grid(before)
        self.assertEqual(self.obs['screenshot'], before)
        self.assertEqual(Image.open(io.BytesIO(transformed)).size, (1920, 1080))
        self.assertEqual(agent_module.coordinate_grid(before), transformed)
        self.assertNotEqual(before, transformed)

    def test_grid_is_opt_in_and_does_not_change_action_mapping(self):
        self.responses = [response()]
        with patch.dict(os.environ, {'ARBM_G3_COORDINATE_GRID': '1'}):
            _, commands = self.predict()
        self.assertEqual(commands, ['pyautogui.click(x=960, y=540)'])
        self.assertEqual(len(self.calls[0]['messages'][1]['content']), 2)
        self.assertIn('coordinate_ruler', self.calls[0]['messages'][1]['content'][0]['text'])
        terminal = json.loads(self.log.read_text().splitlines()[-1])
        self.assertEqual(terminal['screenshot_hash'], hashlib.sha256(self.obs['screenshot']).hexdigest())
        self.assertEqual(terminal['coordinate_reference']['kind'], 'normalized_grid_100_v1')

    def test_default_keeps_original_model_image(self):
        self.responses = [response()]
        with patch.dict(os.environ, {'ARBM_G3_COORDINATE_GRID': '0'}):
            self.predict()
        self.assertEqual(self.agent._model_screenshot, self.obs['screenshot'])

    def test_square_padding_and_inverse_projection_preserve_original_gui_points(self):
        original = self.obs['screenshot']
        square, frame = agent_module.square_observation(original)
        self.assertEqual(Image.open(io.BytesIO(square)).size, (1280, 1280))
        self.assertEqual(frame['original_width'], 1920)
        self.assertEqual(frame['original_height'], 1080)
        self.assertEqual(self.obs['screenshot'], original)
        for params in ({'x': 500, 'y': 500}, {'x': 250, 'y': 750},
                       {'start_x': 50, 'start_y': 250, 'end_x': 950, 'end_y': 750}):
            model = agent_module.project_parameters(params, frame, to_original=False)
            returned = agent_module.project_parameters(model, frame, to_original=True)
            for key in params:
                self.assertLessEqual(abs(params[key] - returned[key]), 1)

    def test_square_maps_synthetic_probe_to_original_unchanged_target(self):
        image = io.BytesIO()
        Image.new('RGB', (400, 240), 'white').save(image, format='PNG')
        self.obs = {'screenshot': image.getvalue()}
        self.responses = [response([payload(x=650, y=450)])]
        with patch.dict(os.environ, {'ARBM_G3_SQUARE_OBSERVATION': '1'}):
            text, commands = self.predict()
        self.assertEqual(json.loads(text)['parameters'], {'x': 650, 'y': 417})
        self.assertEqual(commands, ['pyautogui.click(x=260, y=100)'])
        terminal = json.loads(self.log.read_text().splitlines()[-1])
        self.assertEqual(terminal['model_action_before_projection']['parameters']['y'], 450)

    def test_square_rejects_actions_in_padding_without_dispatch(self):
        self.responses = [response([payload(x=500, y=10)])] * 3
        with patch.dict(os.environ, {'ARBM_G3_SQUARE_OBSERVATION': '1'}):
            with self.assertRaisesRegex(RuntimeError, 'STRUCTURAL_RETRY_EXHAUSTED'):
                self.predict()
        self.assertEqual(len(self.agent._history), 0)
        self.assertIn('COORDINATE_IN_PADDING', self.log.read_text())

    def test_square_ocr_and_history_share_model_frame(self):
        ocr = {'state': 'DERIVED_FROM_SCREENSHOT', 'labels': [{'text': 'Button', 'x': 500, 'y': 250}]}
        with patch.dict(os.environ, {'ARBM_G3_SQUARE_OBSERVATION': '1'}):
            with patch.object(agent_module, 'screenshot_ocr', return_value=ocr):
                self.agent._screen(self.obs['screenshot'])
            self.agent._history.append({'action': 'click', 'parameters': {'x': 500, 'y': 250},
                                        'target': 'Button', 'expected_change': 'Selected', 'signature': 'original'})
            messages = self.agent._messages_for(self.obs['screenshot'], None)
        summary = json.loads(messages[1]['content'][0]['text'])
        self.assertEqual(summary['screen_pixels'], [1280, 1280])
        label = summary['visible_text_from_same_screenshot']['labels'][0]
        action = summary['recent_actions_issued_verify_effect'][0]
        self.assertEqual(label['y'], action['parameters']['y'])
        self.assertNotEqual(label['y'], 250)
        self.assertEqual(self.agent._context['ocr']['labels'][0]['y'], 250)

    def test_square_portrait_and_non_positional_actions(self):
        image = io.BytesIO()
        Image.new('RGB', (240, 400), 'white').save(image, format='PNG')
        _, frame = agent_module.square_observation(image.getvalue())
        self.assertEqual(frame['left'], 80)
        self.assertEqual(frame['top'], 0)
        self.assertEqual(agent_module.project_parameters({'x': 450, 'y': 650}, frame, to_original=True),
                         {'x': 417, 'y': 650})
        for params in ({}, {'text': 'ordinary text'}, {'keys': ['ctrl', 's']}):
            self.assertEqual(agent_module.project_parameters(params, frame, to_original=True), params)

    def test_groq_quota_numeric_cause_is_preserved_without_error_body(self):
        error = RuntimeError('unused')
        error.status_code = 429
        error.body = {'error': {'message': 'Rate limit reached for model in organization private-id on tokens per minute (TPM): Limit 8000, Used 4000, Requested 5000.'}}
        details = agent_module.provider_error_details(error)
        self.assertEqual(details['quota_scope'], 'TOKENS_PER_MINUTE')
        self.assertEqual(details['quota_values'], {'limit': 8000, 'used': 4000, 'requested': 5000})
        self.assertNotIn('private-id', json.dumps(details))


if __name__ == '__main__':
    unittest.main()
