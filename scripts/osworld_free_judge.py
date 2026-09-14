"""FREE-only backend for the upstream's documented evaluation-model API.

Never writes scores or changes evaluator logic. Original messages and raw model
response remain available for independent auditing, including negative verdicts.
"""
import hashlib
import json
import os
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from osworld_openrouter_free import FREE_ROUTE
from osworld_groq_free import GROQ_FREE_ROUTE
from osworld_local_vlm import LOCAL_VLM_ROUTE


def complete(request, route=FREE_ROUTE):
    if not isinstance(request,dict):raise ValueError('JUDGE_REQUEST_OBJECT_REQUIRED')
    messages=request.get('messages')
    if not isinstance(messages,list) or not messages or any(not isinstance(m,dict) or m.get('role') not in ('system','user','assistant') for m in messages): raise ValueError('JUDGE_MESSAGES_REQUIRED')
    tokens=request.get('max_completion_tokens',request.get('max_tokens',512))
    if type(tokens)!=int or not 1<=tokens<=8192: raise ValueError('JUDGE_OUTPUT_BUDGET_INVALID')
    routes=(GROQ_FREE_ROUTE, route, LOCAL_VLM_ROUTE) if route is FREE_ROUTE else (route,)
    attempts=[]; result=None
    for candidate in routes:
        result,current=candidate.call({},budget=105,raw_messages=messages,
            raw_tokens=tokens,temperature=request.get('temperature',0))
        attempts.extend(current)
        if result: break
    return result,attempts


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_):pass

    def reply(self,status,data):
        raw=json.dumps(data).encode()
        self.send_response(status);self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)

    def do_GET(self):
        self.reply(200,{'status':'ok','role':'independent-evaluation-model','spend_mode':os.environ.get('ARBM_VALIDATION_SPEND_MODE','zero')})

    def do_POST(self):
        if self.path!='/v1/chat/completions':return self.reply(404,{})
        if os.environ.get('ARBM_VALIDATION_SPEND_MODE','zero') != 'zero':
            return self.reply(503,{'error':{'message':'VALIDATION_SPEND_MODE_INVALID'}})
        if self.headers.get('Authorization')!='Bearer zero-spend-oidc-shim':return self.reply(401,{'error':{'message':'LOCAL_JUDGE_AUTH_REQUIRED'}})
        self.close_connection=True;self.connection.settimeout(60)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=32*1024**2:raise ValueError('JUDGE_INPUT_BUDGET')
            raw=self.rfile.read(length)
            if len(raw)!=length:raise ValueError('TRUNCATED_JUDGE_INPUT')
            request=json.loads(raw)
            directory=Path(os.environ['ARBM_JUDGE_EVIDENCE']);directory.mkdir(parents=True,exist_ok=True)
            index=len(list(directory.glob('call-*-request.json')))
            prefix=directory/('call-%04d'%index)
            prefix.with_name(prefix.name+'-request.json').write_bytes(raw)
            result,attempts=complete(request)
            event={'task_id':os.environ.get('TASK_ID'),'candidate_sha':os.environ.get('GITHUB_SHA'),
                'status':'REAL_FREE_MODEL_RESPONSE' if result else 'MODEL_ROUTES_UNAVAILABLE',
                'request_sha256':hashlib.sha256(raw).hexdigest(),'provider_attempts':attempts,
                'mandatory_cost_usd':(result or {}).get('mandatory_cost_usd',0),
                'paid_fallback_used':bool((result or {}).get('paid_fallback_used',False))}
            if result:
                response=result['raw_response']
                prefix.with_name(prefix.name+'-response.json').write_text(json.dumps(response,ensure_ascii=False),encoding='utf-8')
                event.update(provider=result['provider'],model=result['model'],response_text=result['text'])
            prefix.with_name(prefix.name+'-telemetry.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
            print(json.dumps(event,ensure_ascii=False),flush=True)
            if not result:return self.reply(503,{'error':{'message':'ALL_DISCOVERED_FREE_JUDGE_ROUTES_UNAVAILABLE'}})
            # Return the vendor response, not a locally constructed verdict.
            self.reply(200,response)
        except (ValueError,KeyError,TypeError) as exc:
            self.reply(400,{'error':{'message':str(exc)[:200]}})


if __name__=='__main__':
    if os.environ.get('ARBM_VALIDATION_SPEND_MODE','zero') != 'zero':
        raise RuntimeError('VALIDATION_SPEND_MODE_INVALID')
    HTTPServer(('127.0.0.1',8089),Handler).serve_forever()
