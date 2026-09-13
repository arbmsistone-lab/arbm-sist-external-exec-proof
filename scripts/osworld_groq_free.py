"""Direct Groq free-plan vision route with explicit zero-spend evidence."""
import json
import os
import time
import urllib.error
import urllib.request

from osworld_control import canonical_action
from osworld_openrouter_free import prompt

BASE = 'https://api.groq.com/openai/v1'
ROUTE = 'groq-multimodal-free'
MODELS = ('qwen/qwen3.8-27b', 'qwen/qwen3.6-27b')


class GroqFreeRoute:
    def __init__(self, transport=None, clock=time.monotonic):
        self.transport = transport or self.http
        self.clock = clock
        self.until = 0

    @staticmethod
    def http(path, key, payload=None, timeout=35):
        request = urllib.request.Request(BASE + path,
            headers={'Authorization':'Bearer ' + key, 'Content-Type':'application/json'},
            data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode())
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.status, json.loads(response.read()), dict(response.headers)
        except urllib.error.HTTPError as error:
            try: data = json.loads(error.read())
            except (ValueError, UnicodeError): data = {}
            return error.code, data, dict(error.headers)
        except (urllib.error.URLError, TimeoutError, ValueError):
            return 503, {}, {}

    def call(self, body, key=None, budget=55, raw_messages=None, raw_tokens=512, temperature=0):
        key = key if key is not None else os.environ.get('GROQ_API_KEY', '')
        attempts = []
        def event(**fields):
            attempts.append({'route':ROUTE, 'mandatory_cost_usd':0,
                'paid_fallback_used':False, **fields})
        if os.environ.get('ZERO_SPEND_MODE') != 'HARD':
            event(status='hard_mode_required'); return None, attempts
        if not key:
            event(status='not_configured'); return None, attempts
        if self.clock() < self.until:
            event(status='provider_cooldown'); return None, attempts
        if raw_messages is None and not body.get('screenshot_data_url', '').startswith('data:image/'):
            event(status='image_required'); return None, attempts
        deadline = self.clock() + budget
        for model in MODELS:
            remaining = deadline - self.clock()
            if remaining < 2: break
            messages = raw_messages if raw_messages is not None else [{'role':'user','content':[
                {'type':'text','text':prompt(body)},
                {'type':'image_url','image_url':{'url':body['screenshot_data_url']}}]}]
            payload = {'model':model, 'messages':messages, 'temperature':temperature,
                       'max_completion_tokens':raw_tokens if raw_messages is not None else 1600,
                       'response_format':{'type':'json_object'}}
            if raw_messages is not None:
                payload.pop('response_format')
            before = self.clock()
            status, data, headers = self.transport('/chat/completions', key, payload,
                                                   timeout=min(35, remaining))
            text = None
            error = ''
            if status == 200:
                try:
                    text = data['choices'][0]['message']['content'].strip()
                    if text.startswith('```'): text = text.split('\n', 1)[1].rsplit('```', 1)[0]
                    action = {'text':text} if raw_messages is not None else canonical_action(json.loads(text))
                except (KeyError, IndexError, TypeError, ValueError) as exc:
                    action = None; error = str(exc)[:150]
            else:
                action = None
            event(model=model, status=status, zero_spend_confirmed=(status == 200 and action is not None),
                  free_plan='groq-free', parsed=action is not None, contract_error=error,
                  latency_seconds=round(self.clock()-before, 3),
                  retry_after=headers.get('retry-after'),
                  remaining_requests=headers.get('x-ratelimit-remaining-requests'))
            if action is not None:
                result = {'provider':'groq-free','model':model,'raw_response':data}
                result.update({'text':text} if raw_messages is not None else {'action':action})
                return result, attempts
            if status in (401, 403):
                self.until = self.clock() + 300
                break
            if status == 429:
                self.until = self.clock() + max(30, float(headers.get('retry-after', 60) or 60))
        return None, attempts


GROQ_FREE_ROUTE = GroqFreeRoute()
