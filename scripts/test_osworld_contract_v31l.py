import ast
from pathlib import Path
p=Path(__file__).with_name('osworld_free_mesh_shim.py')
s=p.read_text(encoding='utf-8')
assert '"phase": "execute"' in s
assert 'ACTION CONTRACT:' in s
assert 'return "FAIL"' in s
assert '"code": "arbm_no_progress_abort"' in s
assert '"code": "shim_internal_error"' in s
assert 'if len(text) > 24000:' in s
assert 'http == 422' in s and 'INVALID_ACTION' in s and 'ACTION_REJECTED' in s
assert 'return "```python\\n" + command + "\\n```"' in s
ast.parse(s)
print('CONTRACT_STATIC_PASS')
