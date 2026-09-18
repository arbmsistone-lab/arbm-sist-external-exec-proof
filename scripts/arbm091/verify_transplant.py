"""Check ancestry and file scope from the new clean branch, never PR #87."""
import json
import hashlib
import subprocess
from pathlib import Path

BASE = 'cf008c04e9bf01e87fca80799dfc25b1de68d888'
PATCH_SOURCE = '04c15b7d30e6dbae62c831e363bced71240aa075'


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def main():
    if git('merge-base', BASE, 'HEAD') != BASE:
        raise SystemExit('BASE_ANCESTRY_MISMATCH')
    if git('rev-list', '--count', BASE + '..HEAD') != '3':
        raise SystemExit('EXACTLY_THREE_CLEAN_COMMITS_REQUIRED')
    if git('rev-list', '--merges', BASE + '..HEAD'):
        raise SystemExit('MERGE_COMMITS_FORBIDDEN')
    manifest = json.loads(Path('audit/arbm091-final-files.json').read_text())
    changed = set(git('diff', '--name-only', BASE, 'HEAD').splitlines())
    if changed != set(manifest):
        raise SystemExit('CHANGED_FILE_ALLOWLIST_MISMATCH')
    # A snapshot import is not an ancestry merge. If the old source happens to
    # be fetched, still require that it is not an ancestor of the candidate.
    exists = subprocess.run(['git', 'cat-file', '-e', PATCH_SOURCE], capture_output=True).returncode == 0
    if exists and subprocess.run(['git', 'merge-base', '--is-ancestor', PATCH_SOURCE, 'HEAD']).returncode == 0:
        raise SystemExit('POLLUTED_SOURCE_HISTORY_IMPORTED')
    dependencies = json.loads(Path('audit/arbm091-dependencies.json').read_text())
    if dependencies['base_sha'] != BASE or dependencies['historical_commits_imported'] != 0:
        raise SystemExit('DEPENDENCY_PROVENANCE_MISMATCH')
    adjustments = json.loads(Path('audit/arbm091-baseline-adjustments.json').read_text())
    patch = json.loads(Path('audit/arbm091-parser-only.patch.json').read_text())
    if patch['after'] != PATCH_SOURCE or hashlib.sha256(patch['patch'].encode()).hexdigest() != patch['patch_sha256']:
        raise SystemExit('PARSER_PATCH_PROVENANCE_MISMATCH')
    expected = {row['path']: row['sha256'] for row in dependencies['files']}
    expected.update({row['path']: row['after_sha256'] for row in adjustments})
    expected.update(patch['postimage_sha256'])
    for path, wanted in expected.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != wanted:
            raise SystemExit('TRANSPLANTED_DEPENDENCY_HASH_MISMATCH:' + path)
    print(json.dumps({'status': 'CLEAN_HISTORY_AND_SCOPE_PASS', 'base_sha': BASE,
                      'new_commits': 3, 'changed_files': len(changed)}))


if __name__ == '__main__':
    main()
