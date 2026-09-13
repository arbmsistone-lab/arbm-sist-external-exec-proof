"""Bounded paid OpenRouter route for explicit G3 validation only."""
import json
import os
import time
from pathlib import Path
import urllib.error
import urllib.request

from osworld_control import canonical_action
from osworld_openrouter_free import prompt

BASE = 'https://openrouter.ai/api/v1'
ROUTE = 'openrouter-multimodal-paid'
DEFAULT_MODEL = 'google/gemini-2.5-flash'
ALLOWED_MODELS = {DEFAULT_MODEL}
ABSOLUTE_CLOSURE_CAP_USD = 8.50


def _money(value):
    try:
        return max(0.0, float(value))
    except (TypeError, ValueError):
        return 0.0


def _ledger_spent(path):
    if not path:
        return None
    try:
        return _money(Path(path).read_text(encoding='utf-8').strip())
    except FileNotFoundError:
        return 0.0


def _ledger_charge(path, cost, cap):
    if not path:
        return None
    import fcntl
    p=Path(path); p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('a+', encoding='utf-8') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0); spent=_money(handle.read().strip())
        if spent + cost > cap:
            return False, spent
        spent += cost; handle.seek(0); handle.truncate(); handle.write(f'{spent:.8f}')
        handle.flush(); os.fsync(handle.fileno())
        return True, spent


class PaidRoute:
    def __init__(self, transport=None, clock=time.monotonic):
        self.transport = transport or self.http
        self.clock = clock
        self.spent = 0.0
    @staticmethod
    def http(path, key, payload=None, timeout=35):
        headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
        req = urllib.request.Request(BASE + path, headers=headers,
            data=None if payload is None else json.dumps(payload, ensure_ascii=False).encode())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.status, json.loads(response.read()), dict(response.headers)
        except urllib.error.HTTPError as error:
            try:
                data = json.loads(error.read())
            except (ValueError, UnicodeError):
                data = {}
            return error.code, data, dict(error.headers)
        except (urllib.error.URLError, TimeoutError, ValueError):
            return 503, {}, {}

    def call(self, body, key=None, budget=55, raw_messages=None, raw_tokens=512, temperature=0):
        attempts = []
        mode = os.environ.get('ARBM_VALIDATION_SPEND_MODE', 'zero')
        key = key if key is not None else os.environ.get('OPENROUTER_API_KEY', '')
        model = os.environ.get('ARBM_PAID_MODEL', DEFAULT_MODEL)
        total_cap = min(_money(os.environ.get('ARBM_PAID_TOTAL_BUDGET_USD', '10')), ABSOLUTE_CLOSURE_CAP_USD)
        ledger = os.environ.get('ARBM_PAID_LEDGER', '')
        shared_spent = _ledger_spent(ledger)
        request_cap = _money(os.environ.get('ARBM_PAID_REQUEST_MAX_USD', '0.25'))
        def event(**fields):
            attempts.append({'route': ROUTE, 'paid_route_proven': True, **fields})
        if mode != 'paid-bounded':
            event(status='paid_mode_required'); return None, attempts
        if not key:
            event(status='not_configured'); return None, attempts
        if model not in ALLOWED_MODELS:
            event(status='model_not_allowlisted', model=model); return None, attempts
        if raw_messages is None and not body.get('screenshot_data_url', '').startswith('data:image/'):
            event(status='image_required'); return None, attempts
        effective_spent = self.spent if shared_spent is None else shared_spent
        if total_cap <= 0 or request_cap <= 0 or effective_spent >= total_cap:
            event(status='budget_exhausted', spent_usd=round(effective_spent,6)); return None, attempts
        messages = raw_messages if raw_messages is not None else [{'role':'user','content':[
            {'type':'text','text':prompt(body)},
            {'type':'image_url','image_url':{'url':body['screenshot_data_url']}}]}]
        payload = {'model': model, 'messages': messages,
            'temperature':temperature if raw_messages is not None else 0,
            'max_tokens':raw_tokens if raw_messages is not None else 1200,
            'provider':{'allow_fallbacks':True, 'require_parameters':True,
                        'only':['google-vertex','google-ai-studio'],
                        'data_collection':'deny', 'zdr':True,
                        'max_price':{'prompt':1.0,'completion':5.0,'image':1.0}}}
        if raw_messages is None:
            payload['response_format']={'type':'json_object'}
        before = self.clock()
        status, data, headers = self.transport('/chat/completions', key, payload,
            timeout=max(.5, min(45, budget)))
        latency = self.clock() - before
        cost = _money((data.get('usage') or {}).get('cost'))
        error = ''; action = None
        if status == 200:
            if cost <= 0:
                error = 'PAID_COST_PROOF_MISSING'
            elif cost > request_cap or effective_spent + cost > total_cap:
                error = 'PAID_BUDGET_EXCEEDED'
            else:
                try:
                    text = data['choices'][0]['message']['content'].strip()
                    if raw_messages is not None:
                        action = {'text':text}
                    else:
                        if text.startswith('```'):
                            text = text.split('\n',1)[1].rsplit('```',1)[0]
                        action = canonical_action(json.loads(text))
                except (KeyError, IndexError, TypeError, ValueError) as exc:
                    error = str(exc)[:150]
        event(model=model, status=status, latency_seconds=round(latency,3),
              usage_cost=cost, request_cap_usd=request_cap, total_cap_usd=total_cap,
              serving_provider=data.get('provider'), contract_error=error,
              retry_after=headers.get('Retry-After', headers.get('retry-after')))
        if action is None:
            return None, attempts
        charged = _ledger_charge(ledger, cost, total_cap)
        if charged is not None:
            ok, shared_total = charged
            if not ok:
                return None, attempts
            self.spent = shared_total
        else:
            self.spent += cost
        if raw_messages is not None:
            return {'text':action['text'], 'provider':'openrouter-paid', 'model':model,
                    'raw_response':data, 'mandatory_cost_usd':cost,
                    'paid_fallback_used':True, 'paid_total_spent_usd':round(self.spent,6)}, attempts
        return {'action': action, 'provider':'openrouter-paid', 'model':model,
                'mandatory_cost_usd':cost, 'paid_fallback_used':True,
                'paid_total_spent_usd':round(self.spent,6)}, attempts


PAID_ROUTE = PaidRoute()
