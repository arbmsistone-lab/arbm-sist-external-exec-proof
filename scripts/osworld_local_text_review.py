"""Pinned open-source text reviewers for fail-closed incident consensus."""
import gc, json, re

MODELS={
 'qwen_local':('Qwen/Qwen2.5-0.5B-Instruct','7ae557604adf67be50417f59c2c2f167def9a775'),
 'smollm_local':('HuggingFaceTB/SmolLM2-360M-Instruct','a10cc1512eabd3dde888204e902eca88bddb4951'),
}

def parse_json(text):
    raw=str(text or '').strip(); dec=json.JSONDecoder()
    for m in re.finditer(r'\{',raw):
        try:
            value,_=dec.raw_decode(raw[m.start():])
            if isinstance(value,dict): return value
        except json.JSONDecodeError: pass
    return None

def review(name, system, evidence, max_new_tokens=320):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    model_id,revision=MODELS[name]
    tok=AutoTokenizer.from_pretrained(model_id,revision=revision)
    model=AutoModelForCausalLM.from_pretrained(model_id,revision=revision,torch_dtype=torch.float32)
    messages=[{'role':'system','content':system},{'role':'user','content':'INCIDENT EVIDENCE\n'+evidence}]
    rendered=tok.apply_chat_template(messages,tokenize=False,add_generation_prompt=True)
    inputs=tok(rendered,return_tensors='pt',truncation=True,max_length=4096)
    with torch.inference_mode():
        generated=model.generate(**inputs,max_new_tokens=max_new_tokens,do_sample=False)
    prompt_tokens=inputs['input_ids'].shape[1]
    text=tok.decode(generated[0,prompt_tokens:],skip_special_tokens=True).strip()
    verdict=parse_json(text)
    meta={'route':name,'model':model_id,'revision':revision,'mandatory_cost_usd':0,
          'paid_fallback_used':False,'compute_scope':'github-public-cloud-runner',
          'prompt_tokens':int(prompt_tokens),'parsed':isinstance(verdict,dict)}
    del generated,inputs,model,tok
    gc.collect()
    return {'verdict':verdict,'attempts':[meta],'raw':text}
