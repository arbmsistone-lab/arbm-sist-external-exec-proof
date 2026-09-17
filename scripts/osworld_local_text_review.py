"""Pinned open-source text reviewers for fail-closed incident consensus.

The local fallback is CPU-only and ZERO_SPEND. Model runtimes are cached with a
strict LRU bound so repeated specialist reviews do not pay model-load cost while
memory growth remains explicitly capped.
"""
import gc
import json
import os
import re
import time
from collections import OrderedDict

MODELS = {
    'qwen_local': ('Qwen/Qwen2.5-0.5B-Instruct', '7ae557604adf67be50417f59c2c2f167def9a775'),
    'smollm_local': ('HuggingFaceTB/SmolLM2-360M-Instruct', 'a10cc1512eabd3dde888204e902eca88bddb4951'),
}
_RUNTIME_CACHE = OrderedDict()


def parse_json(text):
    raw = str(text or '').strip()
    dec = json.JSONDecoder()
    for match in re.finditer(r'\{', raw):
        try:
            value, _ = dec.raw_decode(raw[match.start():])
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            pass
    return None


def _cache_limit():
    try:
        value = int(os.environ.get('ARBM_LOCAL_TEXT_CACHE_MODELS', '1'))
    except ValueError:
        value = 1
    return max(0, min(2, value))


def _token_limit(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = 320
    return max(16, min(512, value))


def clear_runtime_cache():
    """Release cached local models explicitly between independent audit phases."""
    _RUNTIME_CACHE.clear()
    gc.collect()


def _runtime(name):
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM

    if name not in MODELS:
        raise ValueError('LOCAL_TEXT_MODEL_NOT_ALLOWLISTED')
    limit = _cache_limit()
    if limit and name in _RUNTIME_CACHE:
        tokenizer, model = _RUNTIME_CACHE.pop(name)
        _RUNTIME_CACHE[name] = (tokenizer, model)
        return tokenizer, model, True, 0.0

    model_id, revision = MODELS[name]
    started = time.monotonic()
    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, revision=revision, torch_dtype=torch.float32)
    model.eval()
    load_seconds = time.monotonic() - started

    if limit:
        while len(_RUNTIME_CACHE) >= limit:
            _RUNTIME_CACHE.popitem(last=False)
            gc.collect()
        _RUNTIME_CACHE[name] = (tokenizer, model)
    return tokenizer, model, False, load_seconds


def review(name, system, evidence, max_new_tokens=320):
    import torch

    model_id, revision = MODELS.get(name, (None, None))
    if model_id is None:
        raise ValueError('LOCAL_TEXT_MODEL_NOT_ALLOWLISTED')
    tokenizer, model, cache_hit, load_seconds = _runtime(name)
    messages = [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': 'INCIDENT EVIDENCE\n' + evidence},
    ]
    rendered = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(rendered, return_tensors='pt', truncation=True, max_length=4096)
    started = time.monotonic()
    with torch.inference_mode():
        generated = model.generate(
            **inputs, max_new_tokens=_token_limit(max_new_tokens), do_sample=False)
    inference_seconds = time.monotonic() - started
    prompt_tokens = inputs['input_ids'].shape[1]
    text = tokenizer.decode(
        generated[0, prompt_tokens:], skip_special_tokens=True).strip()
    verdict = parse_json(text)
    meta = {
        'route': name,
        'model': model_id,
        'revision': revision,
        'mandatory_cost_usd': 0,
        'paid_fallback_used': False,
        'compute_scope': 'github-public-cloud-runner',
        'prompt_tokens': int(prompt_tokens),
        'parsed': isinstance(verdict, dict),
        'runtime_cache_limit': _cache_limit(),
        'runtime_cache_hit': cache_hit,
        'runtime_load_seconds': round(load_seconds, 3),
        'inference_seconds': round(inference_seconds, 3),
    }
    del generated, inputs
    if not _cache_limit():
        del model, tokenizer
    gc.collect()
    return {'verdict': verdict, 'attempts': [meta], 'raw': text}
