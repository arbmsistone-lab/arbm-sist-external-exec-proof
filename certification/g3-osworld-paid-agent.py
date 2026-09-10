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
        self._fatal_model_error = None

    def reset(self, *args, **kwargs):
        self._previous_obs = None
        self._previous_action = None
        self._action_signatures = []
        self._verifications = []
        self._last_llm_at = 0.0
        self._fatal_model_error = None
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
        if self._fatal_model_error:
            raise RuntimeError(self._fatal_model_error)
        if actions:
            sig=json.dumps(actions,sort_keys=True,default=str)
            if self._action_signatures[-3:].count(sig)>=3:
                actions=['FAIL']
            self._action_signatures.append(sig)
            self._previous_action=actions[0] if actions else None
            self._previous_obs=obs
        return response, actions
    def call_llm(self, payload):
        key=os.environ.get('GEMINI_G3_PAID_CERT_KEY','').strip()
        if not key:
            raise RuntimeError('GEMINI_G3_PAID_CERT_KEY_MISSING')
        messages=payload.get('messages',[]) if isinstance(payload,dict) else []
        system=''
        contents=[]
        for message in messages:
            role=message.get('role','user')
            raw=message.get('content','')
            items=raw if isinstance(raw,list) else [{'type':'text','text':str(raw)}]
            parts=[]
            for item in items:
                if item.get('type')=='text' and item.get('text'):
                    if role=='system': system += ('\n' if system else '') + item['text']
                    else: parts.append({'text':item['text']})
                elif item.get('type')=='image_url':
                    url=str(item.get('image_url',{}).get('url',''))
                    if url.startswith('data:') and ';base64,' in url:
                        head,data=url.split(';base64,',1)
                        parts.append({'inline_data':{'mime_type':head[5:],'data':data}})
            if parts:
                contents.append({'role':'model' if role=='assistant' else 'user','parts':parts})
        body={'contents':contents,'generationConfig':{'temperature':float(payload.get('temperature',0) or 0),'maxOutputTokens':min(4096,max(16,int(payload.get('max_tokens',512) or 512)))}}
        if system: body['systemInstruction']={'parts':[{'text':system}]}
        min_interval=max(1.0,float(os.environ.get('ARBM_G3_MIN_REQUEST_INTERVAL_SEC','15')))
        elapsed=time.monotonic()-self._last_llm_at
        if self._last_llm_at and elapsed < min_interval:
            time.sleep(min_interval-elapsed)
        self._last_llm_at=time.monotonic()
        url='https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent'
        r=requests.post(url,headers={'x-goog-api-key':key,'Content-Type':'application/json'},json=body,timeout=120)
        if r.status_code == 429:
            self._fatal_model_error='MODEL_RATE_LIMIT'
            raise RuntimeError('MODEL_RATE_LIMIT')
        r.raise_for_status()
        data=r.json()
        text=''.join(p.get('text','') for p in data.get('candidates',[{}])[0].get('content',{}).get('parts',[])).strip()
        if not text:
            raise RuntimeError('EMPTY_MODEL_RESPONSE')
        return text
