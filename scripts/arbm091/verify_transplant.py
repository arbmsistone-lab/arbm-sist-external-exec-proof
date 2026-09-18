"""Verify the immutable three-commit transplant plus two scoped repair commits."""
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml

BASE = 'cf008c04e9bf01e87fca80799dfc25b1de68d888'
PATCH_SOURCE = '04c15b7d30e6dbae62c831e363bced71240aa075'
CLEAN_BASELINE = 'a3307fd28c0e50634b931692b6bb1049b2c0c5c9'
WORKFLOW = '.github/workflows/arbm-091-clean-proof.yml'
VERIFIER = 'scripts/arbm091/verify_transplant.py'
ENVIRONMENT_PREFLIGHT = {
    'name': 'Verify exact 091 observer environment before heavy initialization',
    'shell': 'bash',
    'run': '''set -euo pipefail
test "$TASK_ID" = '091'
test "$ZERO_SPEND_MODE" = 'HARD'
test "$RUNNER_ENVIRONMENT" = 'github-hosted'
test "$ARBM_WPS_OBSERVER" = '1'
printf 'TASK091_ENVIRONMENT_PREFLIGHT_PASS task=%s runner=%s spend=%s\\n' "$TASK_ID" "$RUNNER_ENVIRONMENT" "$ZERO_SPEND_MODE"
''',
}


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def normalize(value):
    if isinstance(value, dict):
        return {key: ('\n'.join(line.rstrip() for line in child.splitlines() if line.strip())
                      if key == 'run' and isinstance(child, str) else normalize(child))
                for key, child in value.items()}
    if isinstance(value, list):
        return [normalize(child) for child in value]
    return value


def verify_workflow_delta():
    original = yaml.safe_load(git('show', CLEAN_BASELINE + ':' + WORKFLOW))
    text = Path(WORKFLOW).read_text()
    current = yaml.safe_load(text)
    expected = copy.deepcopy(original)
    expected['jobs']['focal-091']['env']['TASK_ID'] = '091'
    expected['jobs']['focal-091']['steps'].insert(1, ENVIRONMENT_PREFLIGHT)
    expected['jobs']['proof-tests']['steps'][1]['run'] = (
        'python -m pip install -r scripts/requirements-osworld.txt\n'
        'python -m pip install PyYAML==6.0.2\n')
    require(len(re.findall(r'(?m)^\s+TASK_ID: [\'"]091[\'"]\s*$', text)) == 1,
            'TASK091_MUST_BE_QUOTED_YAML_STRING')
    require(normalize(current) == normalize(expected), 'UNEXPECTED_WORKFLOW_SEMANTIC_DELTA')
    unquoted = re.sub(r'(?m)^(\s+TASK_ID:) [\'"]091[\'"]\s*$', r'\1 091', text)
    require(not re.search(r'(?m)^\s+TASK_ID: [\'"]091[\'"]\s*$', unquoted),
            'TASK091_QUOTING_NEGATIVE_TEST_FAILED')


def main():
    require(git('merge-base', BASE, 'HEAD') == BASE, 'BASE_ANCESTRY_MISMATCH')
    require(git('merge-base', CLEAN_BASELINE, 'HEAD') == CLEAN_BASELINE,
            'CLEAN_BASELINE_ANCESTRY_MISMATCH')
    require(git('rev-list', '--count', BASE + '..' + CLEAN_BASELINE) == '3',
            'EXACTLY_THREE_BASELINE_COMMITS_REQUIRED')
    require(git('rev-list', '--count', BASE + '..HEAD') == '5',
            'EXACTLY_FIVE_AUDITED_COMMITS_REQUIRED')
    require(not git('rev-list', '--merges', BASE + '..HEAD'), 'MERGE_COMMITS_FORBIDDEN')
    overlay = git('rev-list', '--reverse', CLEAN_BASELINE + '..HEAD').splitlines()
    require(len(overlay) == 2, 'EXACTLY_TWO_REPAIR_COMMITS_REQUIRED')
    for commit, allowed in zip(overlay, (VERIFIER, WORKFLOW)):
        require(git('diff-tree', '--no-commit-id', '--name-only', '-r', commit) == allowed,
                'REPAIR_COMMIT_SCOPE_MISMATCH:' + commit)
    require(git('rev-parse', overlay[0] + '^') == CLEAN_BASELINE
            and git('rev-parse', overlay[1] + '^') == overlay[0], 'REPAIR_HISTORY_NOT_LINEAR')
    require(not git('diff', '--name-only', '--diff-filter=D', CLEAN_BASELINE, 'HEAD'),
            'REPAIR_DELETION_FORBIDDEN')
    manifest = json.loads(Path('audit/arbm091-final-files.json').read_text())
    changed = set(git('diff', '--name-only', BASE, 'HEAD').splitlines())
    require(changed == set(manifest), 'CHANGED_FILE_ALLOWLIST_MISMATCH')
    require(set(git('diff', '--name-only', CLEAN_BASELINE, 'HEAD').splitlines())
            == {WORKFLOW, VERIFIER}, 'REPAIR_TOTAL_SCOPE_MISMATCH')
    exists = subprocess.run(['git', 'cat-file', '-e', PATCH_SOURCE], capture_output=True).returncode == 0
    if exists:
        require(subprocess.run(['git', 'merge-base', '--is-ancestor', PATCH_SOURCE, 'HEAD']).returncode != 0,
                'POLLUTED_SOURCE_HISTORY_IMPORTED')
    dependencies = json.loads(Path('audit/arbm091-dependencies.json').read_text())
    require(dependencies['base_sha'] == BASE and dependencies['historical_commits_imported'] == 0,
            'DEPENDENCY_PROVENANCE_MISMATCH')
    adjustments = json.loads(Path('audit/arbm091-baseline-adjustments.json').read_text())
    patch = json.loads(Path('audit/arbm091-parser-only.patch.json').read_text())
    require(patch['after'] == PATCH_SOURCE
            and hashlib.sha256(patch['patch'].encode()).hexdigest() == patch['patch_sha256'],
            'PARSER_PATCH_PROVENANCE_MISMATCH')
    expected = {row['path']: row['sha256'] for row in dependencies['files']}
    expected.update({row['path']: row['after_sha256'] for row in adjustments})
    expected.update(patch['postimage_sha256'])
    for path, wanted in expected.items():
        require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == wanted,
                'TRANSPLANTED_DEPENDENCY_HASH_MISMATCH:' + path)
    verify_workflow_delta()
    print(json.dumps({'status': 'CLEAN_HISTORY_AND_SCOPE_PASS', 'base_sha': BASE,
                      'clean_baseline_sha': CLEAN_BASELINE, 'baseline_commits': 3,
                      'repair_commits': overlay, 'new_commits': 5, 'changed_files': len(changed),
                      'repair_scope': [VERIFIER, WORKFLOW], 'official_score_claimed': False}))


if __name__ == '__main__':
    main()
