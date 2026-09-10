import json
import os
import hashlib
import time
from google import genai
from google.genai import types
from mm_agents.gemini_agent import GeminiFCAgent
from mm_agents.gemini_action_parser import InvalidActionError
from mm_agents.g3_paid_control import error_class, gui_action_violation

INPUT_USD_PER_M = 1.50
OUTPUT_USD_PER_M = 9.00

class CappedGeminiFCAgent(GeminiFCAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cost_usd = 0.0
        self._last_cost_usd = 0.0
        self._cost_cap_usd = float(os.environ.get('ARBM_G3_TASK_COST_CAP_USD', '1.00'))
        self._instruction = ''
        self._context_tail = max(2, int(os.environ.get('ARBM_G3_CONTEXT_TAIL_MESSAGES', '6')))
        self._run_cost_usd = 0.0
        self._call_index = 0
        self._task_index = 0
        self._step_index = 0
        self._terminal_error = None
        self._last_screen = None
        self._screen_changed = None
        self._same_screen_steps = 0

    @staticmethod
    def _usage_value(usage, *names):
        for name in names:
            value = getattr(usage, name, None)
            if value is not None:
                return int(value or 0)
        return None

    def _record(self, row):
        usage_path = os.environ.get('ARBM_G3_USAGE_LOG', '').strip()
        if not usage_path:
            raise RuntimeError('G3_USAGE_JOURNAL_REQUIRED')
        row.update({
            'model': self.model_id, 'agent': 'osworld-official-gemini-fc',
            'call_index': self._call_index, 'task_index': self._task_index,
            'step_index': self._step_index, 'context_messages': len(self.messages),
            'screen_changed': self._screen_changed,
            'run_id': os.environ.get('GITHUB_RUN_ID'),
            'run_sha': os.environ.get('GITHUB_SHA'),
        })
        with open(usage_path, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps(row, separators=(',', ':')) + '\n')
            fh.flush()
            os.fsync(fh.fileno())

    def _system_instruction(self):
        base = super()._system_instruction()
        return base + '''\nPerformance rules:\n- Continue from the current screen state; do not restart completed navigation.\n- Use GUI tools for this desktop task. Do not open a terminal, run shell commands, or install packages.\n- Avoid repeating the same action when the screen did not meaningfully change.\n- Keep waits short (normally <=2 seconds) unless a visible load requires more.\n- Complete the requested end state as soon as enough information is available.'''

    def _compact_context(self):
        if len(self.messages) <= self._context_tail + 1:
            return
        task = self._instruction or 'Continue the original task.'
        summary = types.Content(role='user', parts=[types.Part.from_text(text=(
            'Original task: ' + task + '\n'
            'Earlier interaction history was compacted for efficiency. Continue from the current state shown in the recent observations; do not redo completed work.'
        ))])
        # Keep complete model/tool-response turns, including original signatures.
        # An arbitrary message slice can orphan responses after a parse repair.
        start = max(1, len(self.messages) - self._context_tail)
        while start < len(self.messages) and self.messages[start].role != 'model':
            start += 1
        if start == len(self.messages):
            raise RuntimeError('G3_CONTEXT_TURN_BOUNDARY_MISSING')
        self.messages = [summary] + list(self.messages[start:])

    def predict(self, instruction, obs=None, function_responses=None):
        self._step_index += 1
        screenshot = (obs or {}).get('screenshot')
        if not isinstance(screenshot, bytes):
            raise RuntimeError('G3_SCREENSHOT_REQUIRED')
        screen = hashlib.sha256(screenshot).hexdigest()
        self._screen_changed = None if self._last_screen is None else screen != self._last_screen
        self._same_screen_steps = self._same_screen_steps + 1 if self._screen_changed is False else 0
        self._last_screen = screen
        if self._same_screen_steps >= 4:
            self._record({'event': 'blocked', 'reason': 'SCREEN_UNCHANGED_4_STEPS'})
            raise RuntimeError('G3_NO_VISUAL_PROGRESS')
        return super().predict(instruction, obs, function_responses)

    def _parse_response(self, response):
        # Validate the entire turn before the vendor parser accepts any action.
        for part in self._content_parts(response):
            call = getattr(part, 'function_call', None)
            if call is not None:
                violation = gui_action_violation({
                    'action_type': call.name, 'parameters': dict(call.args or {}),
                })
                if violation:
                    self._record({'event': 'action_rejected', 'reason': violation})
                    raise InvalidActionError(violation + '; use direct GUI actions on the visible application')
        return super()._parse_response(response)

    def reset(self, runtime_logger=None):
        self._cost_usd = 0.0
        self._last_cost_usd = 0.0
        self._instruction = ''
        self._task_index += 1
        self._step_index = 0
        self._last_screen = None
        self._screen_changed = None
        self._same_screen_steps = 0
        # Run spend and terminal provider failure survive task resets.
        return super().reset(runtime_logger)

    def _call_model(self):
        if self._terminal_error:
            raise RuntimeError(self._terminal_error)
        self._compact_context()
        reserve = max(0.05, self._last_cost_usd * 1.5)
        if self._run_cost_usd + reserve >= self._cost_cap_usd:
            raise RuntimeError('G3_TASK_COST_CAP_REACHED')
        self._call_index += 1
        self._record({'event': 'request_started', 'usage_status': 'PENDING'})
        started = time.monotonic()
        try:
            # No hidden application or SDK retries: an ambiguous failure must
            # be reconciled before another request can incur charges.
            response = self.client.models.generate_content(
                model=self.model_id, contents=self.messages,
                config=self._generation_config(),
            )
        except Exception as error:
            self._terminal_error = 'G3_' + error_class(error)
            self._record({
                'event': 'request_failed', 'reason': self._terminal_error,
                'usage_status': 'UNKNOWN', 'call_cost_usd': None,
                'latency_ms': round((time.monotonic() - started) * 1000, 3),
            })
            raise RuntimeError(self._terminal_error) from None
        latency_ms = round((time.monotonic() - started) * 1000, 3)
        usage = getattr(response, 'usage_metadata', None)
        prompt = self._usage_value(usage, 'prompt_token_count', 'promptTokenCount')
        output = self._usage_value(usage, 'candidates_token_count', 'candidatesTokenCount')
        thought = self._usage_value(usage, 'thoughts_token_count', 'thoughtsTokenCount') or 0
        total = self._usage_value(usage, 'total_token_count', 'totalTokenCount')
        if (prompt is None or output is None or total is None or
                min(prompt, output, thought, total) < 0 or total < prompt + output + thought):
            self._terminal_error = 'G3_USAGE_METADATA_INVALID'
            self._record({'event': 'request_failed', 'reason': self._terminal_error,
                          'usage_status': 'UNKNOWN', 'call_cost_usd': None, 'latency_ms': latency_ms})
            raise RuntimeError(self._terminal_error)
        # Unclassified non-prompt tokens are conservatively charged as output.
        thought = total - prompt - output
        call_cost = prompt / 1_000_000 * INPUT_USD_PER_M + (output + thought) / 1_000_000 * OUTPUT_USD_PER_M
        self._cost_usd += call_cost
        self._run_cost_usd += call_cost
        self._last_cost_usd = call_cost
        self._record({
                'event': 'request_completed', 'usage_status': 'RECORDED',
                'prompt_tokens': prompt,
                'output_tokens': output,
                'thought_tokens': thought,
                'total_tokens': prompt + output + thought,
                'call_cost_usd': round(call_cost, 8),
                'cumulative_cost_usd': round(self._run_cost_usd, 8),
                'task_cost_usd': round(self._cost_usd, 8), 'latency_ms': latency_ms,
            })
        return response

class ArbmG3Agent:
    def __init__(self, model=None, max_tokens=None, top_p=None, temperature=None,
                 action_space='pyautogui', observation_type='screenshot',
                 max_trajectory_length=None, client_password='', **kwargs):
        key = os.environ.get('GEMINI_G3_PAID_CERT_KEY', '').strip()
        if not key:
            raise RuntimeError('GEMINI_G3_PAID_CERT_KEY_MISSING')
        self._core = CappedGeminiFCAgent(
            client=genai.Client(api_key=key, http_options=types.HttpOptions(
                timeout=45000, retry_options=types.HttpRetryOptions(attempts=1))),
            model_id='gemini-3.5-flash',
            action_space='pyautogui',
            client_password=client_password or 'osworld-public-evaluation',
            media_res='medium',
            thinking_level='low',
            platform='Ubuntu',
            provider_name='docker',
            screen_width=1920,
            screen_height=1080,
            temperature=None,
            max_tokens=2048,
        )

    @property
    def task_current_date(self):
        return self._core.task_current_date

    @task_current_date.setter
    def task_current_date(self, value):
        self._core.task_current_date = value

    def reset(self, *args, **kwargs):
        runtime_logger = args[0] if args else kwargs.get('runtime_logger')
        return self._core.reset(runtime_logger)

    def predict(self, instruction, obs):
        if not self._core._instruction:
            self._core._instruction = instruction
        response, structured = self._core.predict(instruction, obs)
        commands = [item.get('command') for item in structured if item.get('command')]
        return response, commands

    def __getattr__(self, name):
        return getattr(self._core, name)
