import base64, json, os, subprocess, time
import requests
from mm_agents.agent import PromptAgent

class ArbmG3Agent(PromptAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._previous_obs = None
        self._previous_action = None
        self._action_signatures = []
        self._verifications = []
        self._last_llm_at = 0.0

    def reset(self, *args, **kwargs):
        self._previous_obs = None
        self._previous_action = None
        self._action_signatures = []
        self._verifications = []
        self._last_llm_at = 0.0
        return super().reset(*args, **kwargs)

    def _state(self, obs):
        shot = obs.get('screenshot', b'') if isinstance(obs, dict) else b''
        if isinstance(shot, bytes):
            shot = base64.b64encode(shot).decode('ascii')
        return {'screenshot': shot, 'accessibilityTree': obs.get('accessibility_tree') if isinstance(obs, dict) else None,
                'appState': None, 'url': '', 'title': ''}
    def _verify_previous(self, obs):
        if self._previous_obs is None or self._previous_action is None:
            return None
        payload={'before':self._state(self._previous_obs),'after':self._state(obs),'verify':{'minSignals':1},'risk':'LOW'}
        p=subprocess.run(['node','certification/g3-computer-use-snapshot/verify-bridge.mjs'],input=json.dumps(payload),text=True,capture_output=True,check=True)
        result=json.loads(p.stdout)
        self._verifications.append(result)
        return result

    def predict(self, instruction, obs):
        verification=self._verify_previous(obs)
        if verification and verification.get('decision',{}).get('state')!='VERIFIED':
            instruction += '\nPrevious action produced no verified state transition. Recover by reassessing the current screenshot and choose a different safe action.'
        response, actions = super().predict(instruction, obs)
        if actions:
            sig=json.dumps(actions,sort_keys=True,default=str)
            if self._action_signatures[-3:].count(sig)>=3:
                actions=['FAIL']
            self._action_signatures.append(sig)
            self._previous_action=actions[0] if actions else None
            self._previous_obs=obs
        return response, actions
    def call_llm(self, payload):
        token=os.environ.get('ARBM_G3_OIDC','')
        if not token:
            raise RuntimeError('ARBM_G3_OIDC_MISSING')
        endpoint=os.environ['ARBM_G3_MODEL_ENDPOINT']
        request_payload=dict(payload)
        request_payload['model']='gpt-arbm-g3-fixed'
        min_interval=max(1.0,float(os.environ.get('ARBM_G3_MIN_REQUEST_INTERVAL_SEC','15')))
        elapsed=time.monotonic()-self._last_llm_at
        if self._last_llm_at and elapsed < min_interval:
            time.sleep(min_interval-elapsed)
        for attempt in range(4):
            self._last_llm_at=time.monotonic()
            r=requests.post(endpoint,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},json=request_payload,timeout=120)
            if r.status_code != 429:
                break
            if attempt == 3:
                raise RuntimeError('MODEL_TRANSPORT_429')
            retry_after=r.headers.get('Retry-After','').strip()
            try:
                server_delay=float(retry_after)
            except ValueError:
                server_delay=0.0
            time.sleep(min(60.0,max(min_interval,server_delay,min_interval*(attempt+1))))
        r.raise_for_status()
        data=r.json()
        if data.get('model')!='gemini-3.5-flash':
            raise RuntimeError('MODEL_ID_MISMATCH')
        if data.get('paid_fallback_used') not in (False,None) or data.get('mandatory_cost_usd') not in (0,None):
            raise RuntimeError('ZERO_SPEND_VIOLATION')
        return data['choices'][0]['message']['content']