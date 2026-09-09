"""Fail-closed qualification for Cloudflare concise useful-token capacity."""
MIN_INPUT_TOKENS = 1024
MAX_OUTPUT_TOKENS = 102
ALLOWED_TASKS = {"classification","routing","scoring","extraction","decision","short_json"}


def qualifies(prompt_tokens, max_output_tokens, task_kind):
    numeric = type(prompt_tokens) is int and type(max_output_tokens) is int
    ok = (numeric and prompt_tokens >= MIN_INPUT_TOKENS and
          1 <= max_output_tokens <= MAX_OUTPUT_TOKENS and task_kind in ALLOWED_TASKS)
    return {"status":"PASS" if ok else "REJECT_TO_LONG_LANE",
            "count_as_concise_capacity":bool(ok)}


def live_sample_valid(input_tokens, output_tokens, max_output_tokens):
    numeric = all(type(v) is int for v in (input_tokens, output_tokens, max_output_tokens))
    ok = (numeric and input_tokens >= MIN_INPUT_TOKENS and
          0 <= output_tokens <= max_output_tokens <= MAX_OUTPUT_TOKENS)
    return {"status":"PASS" if ok else "FAIL","useful_tokens":input_tokens + output_tokens if ok else 0}
