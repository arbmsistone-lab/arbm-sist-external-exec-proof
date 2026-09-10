import json
import os
from google import genai
from google.genai import types
from mm_agents.gemini_agent import GeminiFCAgent

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

    @staticmethod
    def _usage_value(usage, *names):
        for name in names:
            value = getattr(usage, name, None)
            if value is not None:
                return int(value or 0)
        return 0

    def _system_instruction(self):
        base = super()._system_instruction()
        return base + '''\nPerformance rules:\n- Continue from the current screen state; do not restart completed navigation.\n- Prefer direct GUI actions over opening a terminal or installing packages.\n- Avoid repeating the same action when the screen did not meaningfully change.\n- Keep waits short (normally <=2 seconds) unless a visible load requires more.\n- Complete the requested end state as soon as enough information is available.'''

    def _compact_context(self):
        if len(self.messages) <= self._context_tail + 1:
            return
        task = self._instruction or 'Continue the original task.'
        summary = types.Content(role='user', parts=[types.Part.from_text(text=(
            'Original task: ' + task + '\n'
            'Earlier interaction history was compacted for efficiency. Continue from the current state shown in the recent observations; do not redo completed work.'
        ))])
        self.messages = [summary] + list(self.messages[-self._context_tail:])

    def reset(self, runtime_logger=None):
        self._cost_usd = 0.0
        self._last_cost_usd = 0.0
        self._instruction = ''
        return super().reset(runtime_logger)

    def _call_model(self):
        self._compact_context()
        reserve = max(0.05, self._last_cost_usd * 1.5)
        if self._cost_usd + reserve >= self._cost_cap_usd:
            raise RuntimeError('G3_TASK_COST_CAP_REACHED')
        response = super()._call_model()
        usage = getattr(response, 'usage_metadata', None)
        prompt = self._usage_value(usage, 'prompt_token_count', 'promptTokenCount') if usage else 0
        output = self._usage_value(usage, 'candidates_token_count', 'candidatesTokenCount') if usage else 0
        thought = self._usage_value(usage, 'thoughts_token_count', 'thoughtsTokenCount') if usage else 0
        call_cost = prompt / 1_000_000 * INPUT_USD_PER_M + (output + thought) / 1_000_000 * OUTPUT_USD_PER_M
        self._cost_usd += call_cost
        self._last_cost_usd = call_cost
        usage_path = os.environ.get('ARBM_G3_USAGE_LOG', '').strip()
        if usage_path:
            row = {
                'prompt_tokens': prompt,
                'output_tokens': output,
                'thought_tokens': thought,
                'total_tokens': prompt + output + thought,
                'call_cost_usd': round(call_cost, 8),
                'cumulative_cost_usd': round(self._cost_usd, 8),
                'model': self.model_id,
                'agent': 'osworld-official-gemini-fc',
                'context_messages': len(self.messages),
            }
            with open(usage_path, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(row, separators=(',', ':')) + '\n')
        return response

class ArbmG3Agent:
    def __init__(self, model=None, max_tokens=None, top_p=None, temperature=None,
                 action_space='pyautogui', observation_type='screenshot',
                 max_trajectory_length=None, client_password='', **kwargs):
        key = os.environ.get('GEMINI_G3_PAID_CERT_KEY', '').strip()
        if not key:
            raise RuntimeError('GEMINI_G3_PAID_CERT_KEY_MISSING')
        self._core = CappedGeminiFCAgent(
            client=genai.Client(api_key=key),
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
            max_tokens=None,
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
