"""Quota-independent open-source VLM fallback for public GitHub cloud runners."""
import base64
import io
import json
import os
import time

from osworld_control import canonical_action
from osworld_openrouter_free import prompt

ROUTE = 'local-cloud-vlm'
MODEL = os.environ.get('ARBM_LOCAL_VLM_MODEL', 'HuggingFaceTB/SmolVLM-256M-Instruct')


def _parts(messages):
    texts=[]; images=[]
    for message in messages or []:
        content=message.get('content') if isinstance(message,dict) else None
        if isinstance(content,str):
            texts.append(content); continue
        for item in content or []:
            if not isinstance(item,dict): continue
            if item.get('type')=='text': texts.append(str(item.get('text') or ''))
            if item.get('type')=='image_url':
                image=item.get('image_url') or {}
                url=image.get('url','') if isinstance(image,dict) else ''
                if url.startswith('data:image/') and ',' in url: images.append(url.split(',',1)[1])
    return '\n'.join(texts),images


def default_infer(text, image_b64, max_tokens):
    import torch
    from PIL import Image
    from transformers import AutoProcessor, AutoModelForImageTextToText
    if not hasattr(default_infer,'runtime'):
        processor=AutoProcessor.from_pretrained(MODEL)
        model=AutoModelForImageTextToText.from_pretrained(MODEL,torch_dtype=torch.float32)
        model.eval()
        default_infer.runtime=(processor,model)
    processor,model=default_infer.runtime
    image=Image.open(io.BytesIO(base64.b64decode(image_b64))).convert('RGB')
    messages=[{'role':'user','content':[{'type':'image'},{'type':'text','text':text}]}]
    rendered=processor.apply_chat_template(messages,add_generation_prompt=True)
    inputs=processor(text=rendered,images=[image],return_tensors='pt')
    with torch.inference_mode():
        generated=model.generate(**inputs,max_new_tokens=max(1,min(int(max_tokens),192)),do_sample=False)
    prompt_tokens=inputs['input_ids'].shape[1]
    return processor.batch_decode(generated[:,prompt_tokens:],skip_special_tokens=True)[0].strip()


class LocalVLMRoute:
    def __init__(self, infer=None, clock=time.monotonic):
        self.infer=infer or default_infer
        self.clock=clock

    def call(self, body, budget=105, raw_messages=None, raw_tokens=512, temperature=0):
        attempts=[]
        base={'route':ROUTE,'model':MODEL,'mandatory_cost_usd':0,'paid_fallback_used':False,
              'compute_scope':'github-public-cloud-runner'}
        if os.environ.get('ZERO_SPEND_MODE')!='HARD':
            return None,[{**base,'status':'hard_mode_required'}]
        if os.environ.get('ARBM_ENABLE_LOCAL_VLM')!='1':
            return None,[{**base,'status':'disabled'}]
        if raw_messages is not None:
            text,images=_parts(raw_messages)
        else:
            url=body.get('screenshot_data_url','')
            text=prompt(body); images=[url.split(',',1)[1]] if url.startswith('data:image/') and ',' in url else []
        if not images:
            return None,[{**base,'status':'image_required'}]
        started=self.clock()
        try:
            output=self.infer(text,images[-1],raw_tokens if raw_messages is not None else 160)
            if self.clock()-started>budget:
                return None,[{**base,'status':'budget_exceeded'}]
            if raw_messages is not None:
                action={'text':str(output).strip()}
            else:
                raw=str(output).strip()
                if raw.startswith('```'): raw=raw.split('\n',1)[1].rsplit('```',1)[0]
                action={'action':canonical_action(json.loads(raw))}
        except Exception as exc:
            return None,[{**base,'status':'local_model_error','error_type':type(exc).__name__}]
        if raw_messages is not None:
            result={'provider':'local-cloud-vlm','model':MODEL,'text':action['text']}
            raw_response={'choices':[{'message':{'role':'assistant','content':action['text']}}]}
        else:
            result={'provider':'local-cloud-vlm','model':MODEL,'action':action['action']}
            raw_response={'choices':[{'message':{'role':'assistant','content':json.dumps(action['action'])}}]}
        result['raw_response']=raw_response
        attempts.append({**base,'status':200,'zero_spend_confirmed':True,
                         'latency_seconds':round(self.clock()-started,3)})
        return result,attempts


LOCAL_VLM_ROUTE=LocalVLMRoute()
