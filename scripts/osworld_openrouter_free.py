"""Independent FREE-only multimodal route; no paid model or credit fallback."""
import hashlib
import json
import math
import os
import time
import urllib.error
import urllib.request
from osworld_control import canonical_action

BASE = 'https://openrouter.ai/api/v1'
ROUTE = 'openrouter-multimodal-free'
PREFERRED = ['nex-agi/nex-n2.5-pro:free', 'thinkingmachines/inkling:free',
             'google/gemma-4-31b-it:free', 'inclusionai/ling-3.0-flash-vl:free',
             'nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free']
# The catalog changes more quickly than this source file.  Keep the models
# proven during admission first, then admit a bounded set of newly listed
# FREE vision models only when their catalog metadata passes `eligible`.
MAX_FREE_CANDIDATES = 16


def zero(value):
    if isinstance(value, bool): return False
    try: return math.isfinite(float(value)) and float(value) == 0
    except (ValueError, TypeError): return False


def eligible(model):
    pricing = model.get('pricing') or {}
    return (str(model.get('id', '')).endswith(':free')
            and zero(pricing.get('prompt')) and zero(pricing.get('completion'))
            and all(zero(v) for v in pricing.values())
            and 'image' in model.get('architecture', {}).get('input_modalities', [])
            and 'text' in model.get('architecture', {}).get('output_modalities', [])
            and model.get('context_length', 0) >= 16000)


def prompt(body):
    return '''Control the visible Ubuntu desktop by GUI only. Return ONE JSON object.
Choose the next unmet subtask. Read required source records before editing output.
The screenshot identifies foreground; the accessibility tree can include occluded
background controls. Use visible target centers or keyboard navigation. Bring
windows forward before clicking them. An issued action is not proof of completion.
Use only direct literal pyautogui calls, at most four tightly related calls, as a
STRING. No shell, terminal, scripts, filesystem/network APIs, clipboard extraction,
hidden state or benchmark internals. Typing a path in a visible file dialog is
allowed. Scroll by 3-6; sleep at most 3 seconds. Never repeat an ineffective action.
Remember only facts visible in the current source; consult verified milestones.
Finish only when all requested outputs are visibly verified.
JSON fields: action (exec|wait|finish), command (string), plan, summary, verification
(observed result of previous action), expected_change, confidence, observed_facts
([{quote: exact text from CURRENT accessibility}]), checkpoint
({name,application,visible_text: exact expected NEXT foreground evidence}).
All other descriptive fields are short factual STRINGS.
''' + '\nCURRENT REQUEST:\n' + json.dumps({k: body.get(k) for k in
        ('instruction', 'active_application', 'observation', 'memory',
         'previous_command', 'verified_milestones', 'recovery_strategy',
         'verifier', 'image_geometry')}, ensure_ascii=False)


class FreeRoute:
    def __init__(self, transport=None, clock=time.monotonic):
        self.transport = transport or self.http
        self.clock = clock
        self.models = []
        self.catalog_until = 0
        self.catalog_hash = ''
        self.auth_until = 0
        self.states = {}
        self.provider_until = 0

    @staticmethod
    def http(path, key, payload=None, timeout=35):
        headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
        request = urllib.request.Request(BASE + path, headers=headers,
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

    def state(self, model):
        return self.states.setdefault(model, {'state':'DEGRADED', 'until':0,
            'failures':0, 'successes':0, 'latency_seconds':35, 'remaining':None})

    def failure(self, model, status, headers):
        state = self.state(model)
        state['failures'] += 1
        reason = {401:'AUTH_FAILED', 403:'AUTH_FAILED', 402:'QUOTA_EXHAUSTED',
                  429:'RATE_LIMITED', 404:'TEMPORARILY_DISABLED', 413:'TEMPORARILY_DISABLED'}.get(status, 'DEGRADED')
        try: delay = min(3600, max(30, float(headers.get('Retry-After', headers.get('retry-after', 60)))))
        except (ValueError, TypeError): delay = 60
        if status in (401,403,404,413): delay = 300
        state.update(state=reason, until=self.clock()+delay)
        if status in (401,403,402): self.provider_until = self.clock()+delay

    def call(self, body, key=None, budget=55, raw_messages=None, raw_tokens=512, temperature=0):
        key = key if key is not None else os.environ.get('OPENROUTER_API_KEY', '')
        attempts = []
        def event(**fields):
            attempts.append({'route':ROUTE, 'mandatory_cost_usd':0,
                'paid_fallback_used':False, **fields})
        if os.environ.get('ZERO_SPEND_MODE') != 'HARD':
            event(status='hard_mode_required'); return None, attempts
        if not key:
            event(status='not_configured'); return None, attempts
        if self.clock() < self.provider_until:
            event(status='provider_cooldown'); return None, attempts
        if raw_messages is None and not body.get('screenshot_data_url', '').startswith('data:image/'):
            event(status='image_required'); return None, attempts
        deadline = self.clock()+budget
        if self.clock() >= self.auth_until:
            status, data, headers = self.transport('/key', key, timeout=max(.5,min(15,deadline-self.clock())))
            if status != 200 or not isinstance(data.get('data'), dict):
                event(status='auth_probe_failed', http=status)
                self.failure('*', status, headers); return None, attempts
            self.auth_until = self.clock()+300
            # No label, key, headers, or balances are copied into evidence.
            event(status='auth_probe_pass', account_free_tier=data['data'].get('is_free_tier'))
        if self.clock() >= self.catalog_until:
            if deadline-self.clock()<.5:
                event(status='request_budget_elapsed');return None,attempts
            status, data, _ = self.transport('/models', key, timeout=min(15,deadline-self.clock()))
            if status != 200:
                event(status='catalog_unavailable', http=status); return None, attempts
            eligible_models = [m for m in data.get('data', []) if eligible(m)]
            by_id = {m['id']: m for m in eligible_models}
            preferred = [by_id[name] for name in PREFERRED if name in by_id]
            extras = sorted((m for m in eligible_models if m['id'] not in PREFERRED),
                            key=lambda m: m['id'])
            self.models = (preferred + extras)[:MAX_FREE_CANDIDATES]
            self.catalog_hash = hashlib.sha256(json.dumps(self.models, sort_keys=True).encode()).hexdigest()
            self.catalog_until = self.clock()+300
        models = sorted(self.models, key=lambda m: (self.state(m['id'])['failures'] /
            (1+self.state(m['id'])['successes']),
            PREFERRED.index(m['id']) if m['id'] in PREFERRED else len(PREFERRED),
            self.state(m['id'])['latency_seconds'], m['id']))
        for model in models:
            name = model['id']; state = self.state(name)
            external_until = float((body.get('route_cooldowns') or {}).get(ROUTE+':'+name, 0))/1000
            if self.clock() < state['until'] or time.time() < external_until:
                event(model=name, status='cooldown', circuit=state['state']); continue
            remaining = deadline-self.clock()
            if remaining < 2: break
            state['state'] = 'HALF_OPEN' if state['failures'] else 'DEGRADED'
            payload = {'model':name, 'messages':raw_messages if raw_messages is not None else [{'role':'user','content':[
                {'type':'text','text':prompt(body)}, {'type':'image_url','image_url':{'url':body['screenshot_data_url']}}]}],
                'temperature':0, 'max_tokens':1600,
                'provider':{'allow_fallbacks':True, 'max_price':{'prompt':0,'completion':0,'request':0,'image':0}}}
            if raw_messages is not None:
                # The evaluator's messages, images, system prompt and output
                # budget pass through unchanged. Never retry a valid NO verdict.
                payload.update(messages=raw_messages,max_tokens=raw_tokens,temperature=temperature)
            elif 'response_format' in model.get('supported_parameters', []): payload['response_format'] = {'type':'json_object'}
            if 'reasoning' in model.get('supported_parameters', []): payload['reasoning'] = {'enabled':False}
            before = self.clock()
            status, data, headers = self.transport('/chat/completions', key, payload, timeout=min(35, remaining))
            latency = self.clock()-before
            cost_proven = status == 200 and zero((data.get('usage') or {}).get('cost'))
            action = None; error = ''
            if cost_proven:
                try:
                    text = data['choices'][0]['message']['content']
                    if not isinstance(text,str):raise ValueError('RESPONSE_TEXT_REQUIRED')
                    text=text.strip()
                    if text.startswith('```'): text = text.split('\n',1)[1].rsplit('```',1)[0]
                    action = {'text':text} if raw_messages is not None and text else canonical_action(json.loads(text))
                except (KeyError, IndexError, TypeError, ValueError) as exc: error = str(exc)[:150]
            if status == 200 and not cost_proven:
                # An unproven response is never promoted to a zero-cost action.
                error = 'RESPONSE_ZERO_COST_UNPROVEN'
            event(model=name, status=status, free_plan_proven=cost_proven,
                catalog_sha256=self.catalog_hash, catalog_pricing=model['pricing'],
                context_length=model['context_length'], latency_seconds=round(latency,3),
                usage_cost=(data.get('usage') or {}).get('cost'), parsed=action is not None,
                contract_error=error, retry_after=headers.get('Retry-After', headers.get('retry-after')),
                generation_id=data.get('id'), serving_provider=data.get('provider'), circuit=state['state'])
            if action is not None:
                state.update(state='HEALTHY', failures=0, successes=state['successes']+1,
                    until=0, latency_seconds=latency)
                if raw_messages is not None:
                    return {'text':data['choices'][0]['message']['content'],
                        'provider':'openrouter-free','model':name,'raw_response':data},attempts
                return {'action':action, 'provider':'openrouter-free', 'model':name}, attempts
            self.failure(name, status if status != 200 else 422, headers)
            if status in (401,403,402): break
        return None, attempts


FREE_ROUTE = FreeRoute()
