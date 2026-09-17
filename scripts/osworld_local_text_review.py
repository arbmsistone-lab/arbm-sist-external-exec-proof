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
        value = 160
    return max(16, min(192, value))


def _prompt_token_limit():
    try:
        value = int(os.environ.get('ARBM_LOCAL_TEXT_PROMPT_TOKENS', '2048'))
    except ValueError:
        value = 2048
    return max(512, min(3072, value))


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


def _clip_tokens(tokenizer, text, limit):
    """Keep both causal setup and latest evidence without cutting mid-prompt blindly."""
    text = str(text or '')
    ids = tokenizer.encode(text, add_special_tokens=False)
    if len(ids) <= limit:
        return text
    head = max(1, limit // 2)
    tail = max(1, limit - head)
    first = tokenizer.decode(ids[:head], skip_special_tokens=True)
    last = tokenizer.decode(ids[-tail:], skip_special_tokens=True)
    return first + '\n...[TOKEN-BOUNDED MIDDLE OMITTED]...\n' + last


def _post_focal_messages(tokenizer, system, evidence):
    role_match = re.search(r'(?m)^ROLE=([A-Za-z0-9_]+)\s*$', str(system or ''))
    if not role_match:
        return None, ''
    role = role_match.group(1)
    marker = 'CURRENT CANDIDATE CONTRACT (source excerpts):\n'
    before, sep, contract = str(system).partition(marker)
    if not sep:
        contract = ''
    specialty_match = re.search(r'(?m)^SPECIALTY=(.+)$', before)
    specialty = specialty_match.group(1).strip() if specialty_match else role
    contract = _clip_tokens(tokenizer, contract, 760)
    evidence = _clip_tokens(tokenizer, evidence, 620)
    system_short = (
        'You are a fail-closed OSWorld specialist. Judge only supplied evidence. '
        'Do not invent facts, weaken the evaluator, or propose paid fallback. '
        f'Assigned role: {role}. Specialty: {specialty}.')
    final = (
        'DECIDE NOW. Return one JSON object only. Do not continue or quote source code. '
        f'role must be exactly {role}. verdict must be PASS_FIX, REJECT_FIX, or INSUFFICIENT. '
        'root_cause_class must be AGENT_LOGIC, EVIDENCE_PROVENANCE, IMAGE_QUALITY, GUI_STATE, '
        'EVALUATOR, INFRASTRUCTURE, PROVIDER_CAPACITY, or UNKNOWN. '
        'causal_chain, regression_risks, and required_proofs must be JSON arrays with at most one short item each. '
        'definitive_fix must be a short string. confidence must be 0..1. veto must be true or false. '
        'Choose the verdict from evidence; PASS is not required.')
    user = (
        'CURRENT CANDIDATE CONTRACT:\n' + contract +
        '\n\nAPPROVED/DIAGNOSTIC/HISTORICAL EVIDENCE:\n' + evidence +
        '\n\n' + final)
    prefix = '{"role":"' + role + '","verdict":"'
    return [
        {'role': 'system', 'content': system_short},
        {'role': 'user', 'content': user},
    ], prefix


def review(name, system, evidence, max_new_tokens=160):
    import torch

    model_id, revision = MODELS.get(name, (None, None))
    if model_id is None:
        raise ValueError('LOCAL_TEXT_MODEL_NOT_ALLOWLISTED')
    tokenizer, model, cache_hit, load_seconds = _runtime(name)
    post_focal = os.environ.get('ARBM_POST_FOCAL_COMPACT_LOCAL') == '1'
    prefix = ''
    if post_focal:
        messages, prefix = _post_focal_messages(tokenizer, system, evidence)
    else:
        messages = None
    if not messages:
        messages = [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': 'INCIDENT EVIDENCE\n' + evidence},
        ]
        prefix = ''
    rendered = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True) + prefix
    prompt_limit = _prompt_token_limit()
    old_side = getattr(tokenizer, 'truncation_side', 'right')
    tokenizer.truncation_side = 'left' if post_focal else 'right'
    try:
        inputs = tokenizer(rendered, return_tensors='pt', truncation=True, max_length=prompt_limit)
    finally:
        tokenizer.truncation_side = old_side
    generation_limit = _token_limit(192 if post_focal else max_new_tokens)
    started = time.monotonic()
    with torch.inference_mode():
        generated = model.generate(
            **inputs, max_new_tokens=generation_limit, do_sample=False,
            use_cache=True)
    inference_seconds = time.monotonic() - started
    prompt_tokens = inputs['input_ids'].shape[1]
    completion = tokenizer.decode(
        generated[0, prompt_tokens:], skip_special_tokens=True).strip()
    text = (prefix + completion).strip() if prefix else completion
    verdict = parse_json(text)
    meta = {
        'route': name,
        'model': model_id,
        'revision': revision,
        'mandatory_cost_usd': 0,
        'paid_fallback_used': False,
        'compute_scope': 'github-public-cloud-runner',
        'prompt_tokens': int(prompt_tokens),
        'prompt_token_limit': prompt_limit,
        'max_new_tokens': generation_limit,
        'post_focal_compact_prompt': post_focal,
        'json_prefix_used': bool(prefix),
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
