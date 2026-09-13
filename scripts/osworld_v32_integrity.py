"""Seal official task and evaluator code before execution, compare after."""
import hashlib
import json
from pathlib import Path
import sys


def snapshot(root):
    paths = [root / 'lib_run_single.py']
    for directory in ('evaluation_examples/task_class','desktop_env/evaluators'):
        paths.extend((root / directory).rglob('*.py'))
    if len(paths) < 109: raise RuntimeError('OFFICIAL_EVALUATOR_CODE_INCOMPLETE')
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


if __name__ == '__main__':
    mode, directory, manifest, *rest = sys.argv[1:]
    now = snapshot(Path(directory))
    if mode == 'snapshot': Path(manifest).write_text(json.dumps(now, indent=2))
    elif mode == 'verify':
        before = json.loads(Path(manifest).read_text())
        result = {name: {'before': before.get(name), 'after': now.get(name)} for name in sorted(set(before) | set(now))}
        Path(rest[0]).write_text(json.dumps(result, indent=2))
        if before != now: raise SystemExit('OFFICIAL_EVALUATOR_CHANGED')
    else: raise SystemExit('UNKNOWN_MODE')
