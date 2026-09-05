from pathlib import Path

SRC=Path('supabase/functions/arbm-benchmark-quality-cost-v1/index.ts').read_text(encoding='utf-8')

assert 'gpt-5.6-luna' in SRC
assert 'gpt-5.6-terra' in SRC
assert 'OPENAI_API_KEY' in SRC
assert 'mandatory_cost_usd' in SRC
assert 'refs/heads/p8/' in SRC
assert 'Never use hidden tests' in SRC
assert 'const model=hard?ESCALATION:PRIMARY' in SRC
assert 'store:false' in SRC
assert 'gold patches' in SRC
assert 'quality-cost-v1' in SRC
assert 'PAID_PROVIDER_UNAVAILABLE' in SRC
assert 'WAITING_PAID_CAPACITY' in SRC
print('quality-cost endpoint policy tests: PASS')
