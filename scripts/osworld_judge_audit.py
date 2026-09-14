"""Audit native evaluator inputs against the independent FREE backend receipt."""
import base64
import hashlib
import json
import mimetypes
from osworld_openrouter_free import zero


def signature(messages):
    out=[]
    for message in messages:
        content=message.get('content')
        if isinstance(content,list):
            parts=[]
            for item in content:
                if item.get('type')=='image_url':
                    url=item['image_url']['url']
                    if url.startswith('data:'):
                        parts.append({'image_sha256':hashlib.sha256(base64.b64decode(url.split(',',1)[1],validate=True)).hexdigest()})
                    else:parts.append({'image_url':url})
                else:parts.append(item)
            content=parts
        out.append({'role':message.get('role'),'content':content})
    return out


def audit_judgements(root,task,sha):
    receipts=[]
    for path in sorted((root/'judge').glob('call-*-telemetry.json')):
        event=json.loads(path.read_text())
        if event.get('task_id')!=task or event.get('candidate_sha')!=sha:raise ValueError('JUDGE_PROVENANCE_MISMATCH')
        cost=float(event.get('mandatory_cost_usd') or 0)
        if cost!=0 or event.get('paid_fallback_used') is not False: raise ValueError('JUDGE_COST_UNPROVEN')
        for attempt in event.get('provider_attempts',[]):
            if attempt.get('status')==200 and not (attempt.get('free_plan_proven') is True or attempt.get('zero_spend_confirmed') is True): raise ValueError('JUDGE_ATTEMPT_COST_UNPROVEN')
        prefix=path.name.removesuffix('-telemetry.json')
        raw=(path.parent/(prefix+'-request.json')).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=event.get('request_sha256'):raise ValueError('JUDGE_REQUEST_CHANGED')
        if event.get('status') != 'REAL_FREE_MODEL_RESPONSE': continue
        response=json.loads((path.parent/(prefix+'-response.json')).read_text())
        text=response['choices'][0]['message']['content']
        raw_cost=float(response.get('usage',{}).get('cost') or 0)
        if text!=event.get('response_text') or not zero(raw_cost):raise ValueError('JUDGE_RAW_RESPONSE_CHANGED_OR_COST')
        request=json.loads(raw)
        receipts.append((signature(request['messages']),text.strip()))
    native=list((root/'official-evaluator-raw').glob('call_*.json'))
    for path in native:
        record=json.loads(path.read_text())
        if record.get('call_type')=='chat':messages=record['messages']
        elif record.get('call_type')=='generate_text':
            messages=[]
            if record.get('system'):messages.append({'role':'system','content':record['system']})
            images=record.get('image_paths_saved') or []
            if not images:content=record['prompt']
            else:
                content=[{'type':'text','text':record['prompt']}]
                for i,image in enumerate(images,1):
                    file=path.parent/image.replace('\\','/').rsplit('/',1)[-1]
                    mime=mimetypes.guess_type(file.name)[0] or 'image/png'
                    content.extend([{'type':'text','text':'Image '+str(i)+':'},
                        {'type':'image_url','image_url':{'url':'data:'+mime+';base64,'+base64.b64encode(file.read_bytes()).decode()}}])
            messages.append({'role':'user','content':content})
        else:raise ValueError('UNKNOWN_NATIVE_EVALUATOR_CALL')
        pair=(signature(messages),record['response'].strip())
        if pair not in receipts:raise ValueError('NATIVE_JUDGE_INPUT_OR_RESPONSE_NOT_PROVEN')
    if receipts and not native:raise ValueError('NATIVE_JUDGE_RECEIPT_MISSING')
    return {'native_calls':len(native),'backend_responses':len(receipts),'spend_mode':'HARD','input_and_response_integrity':'PASS'}
