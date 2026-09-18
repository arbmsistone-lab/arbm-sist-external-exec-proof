"""Rebuild only the clean third commit; never update a remote ref."""
from __future__ import annotations
import base64
import datetime
import hashlib
import json
import os
import pathlib
import subprocess

REPO = 'arbmsistone-lab/arbm-sist-external-exec-proof'
BASE = 'cf008c04e9bf01e87fca80799dfc25b1de68d888'
SOURCE = 'a3307fd28c0e50634b931692b6bb1049b2c0c5c9'
PARENT = '56cc05c7df91769e768bac26fa845a4403a441ea'
BRANCH = 'chatgpt/arbm-091-clean-env-contract-20260918'
WORKFLOW = '.github/workflows/arbm-091-clean-proof.yml'
TEST_FILE = 'tests/arbm091/test_runtime_contract.py'
AUDIT_FILE = 'audit/arbm091-runtime-contract-fix.json'
MANIFEST = 'audit/arbm091-final-files.json'
ALLOWED = {WORKFLOW, TEST_FILE, AUDIT_FILE, MANIFEST}
TEMP = pathlib.Path(os.environ['RUNNER_TEMP'])

TESTS = r'''"""Regression for the real workflow's literal task identity and startup guard."""
from __future__ import annotations
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import yaml
from arbm091.wps_observer import install

WORKFLOW = Path('.github/workflows/arbm-091-clean-proof.yml')

def child(node, name):
    return next(value for key, value in node.value if key.value == name)

class WorkflowRuntimeContractTests(unittest.TestCase):
    def test_task_id_has_explicit_yaml_string_style(self):
        node = yaml.compose(WORKFLOW.read_text())
        for key in ('jobs', 'focal-091', 'env', 'TASK_ID'):
            node = child(node, key)
        self.assertEqual(node.value, '091')
        self.assertEqual(node.tag, 'tag:yaml.org,2002:str')
        self.assertIn(node.style, ("'", '"'))

    def test_task_id_value_is_exact(self):
        data = yaml.safe_load(WORKFLOW.read_text())
        self.assertEqual(data['jobs']['focal-091']['env']['TASK_ID'], '091')

    def test_literal_environment_guard_precedes_runtime_preparation(self):
        steps = yaml.safe_load(WORKFLOW.read_text())['jobs']['focal-091']['steps']
        names = [s.get('name', '') for s in steps]
        guard = 'Validate literal task identity before runtime preparation'
        self.assertIn(guard, names)
        self.assertLess(names.index(guard), names.index('Prepare pinned shim runtime'))
        self.assertIn('test "$TASK_ID" = \'091\'', steps[names.index(guard)]['run'])
        self.assertNotIn('continue-on-error', steps[names.index(guard)])

    def test_pinned_observer_import_precedes_vm_download(self):
        steps = yaml.safe_load(WORKFLOW.read_text())['jobs']['focal-091']['steps']
        names = [s.get('name', '') for s in steps]
        check = 'Validate observer import in pinned upstream runtime before VM'
        self.assertIn(check, names)
        self.assertLess(names.index(check), names.index('Download pinned official VM'))
        self.assertGreater(names.index(check), names.index('Apply exact upstream runtime patches'))
        self.assertNotIn('continue-on-error', steps[names.index(check)])

class ObserverStartupContractTests(unittest.TestCase):
    def make_environment(self):
        class Environment:
            def step(self, action, pause=2):
                raise AssertionError('startup check must not execute a GUI action')
        return Environment

    def environment(self):
        return {'RUNNER_ENVIRONMENT': 'github-hosted', 'ZERO_SPEND_MODE': 'HARD', 'TASK_ID': '091'}

    def test_exact_remote_zero_spend_task_installs_without_gui_execution(self):
        environment = self.make_environment()
        original = environment.step
        with patch.dict(os.environ, self.environment(), clear=True):
            install(environment)
        self.assertTrue(environment._arbm091_observed)
        self.assertIsNot(environment.step, original)

    def test_duplicate_install_preserves_single_wrapper(self):
        environment = self.make_environment()
        with patch.dict(os.environ, self.environment(), clear=True):
            install(environment)
            first = environment.step
            install(environment)
        self.assertIs(environment.step, first)

    def test_noncanonical_and_wrong_task_ids_are_rejected(self):
        for value in ('91', '0091', '091 ', '090', ''):
            with self.subTest(task=value):
                env = self.environment()
                env['TASK_ID'] = value
                environment = self.make_environment()
                original = environment.step
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaisesRegex(ValueError, 'OBSERVER_REMOTE_ZERO_SPEND_TASK091_REQUIRED'):
                        install(environment)
                self.assertIs(environment.step, original)

    def test_nonfree_modes_are_rejected(self):
        for value in ('SOFT', 'PAID', ''):
            with self.subTest(mode=value):
                env = self.environment()
                env['ZERO_SPEND_MODE'] = value
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaisesRegex(ValueError, 'OBSERVER_REMOTE_ZERO_SPEND_TASK091_REQUIRED'):
                        install(self.make_environment())

    def test_local_and_unknown_runners_are_rejected(self):
        for value in ('self-hosted', 'local', ''):
            with self.subTest(runner=value):
                env = self.environment()
                env['RUNNER_ENVIRONMENT'] = value
                with patch.dict(os.environ, env, clear=True):
                    with self.assertRaisesRegex(ValueError, 'OBSERVER_REMOTE_ZERO_SPEND_TASK091_REQUIRED'):
                        install(self.make_environment())

    def test_missing_environment_is_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, 'OBSERVER_REMOTE_ZERO_SPEND_TASK091_REQUIRED'):
                install(self.make_environment())

if __name__ == '__main__':
    unittest.main()
'''

ENV_GUARD = '''    - name: Validate literal task identity before runtime preparation
      shell: bash
      run: |
        set -euo pipefail
        test "$TASK_ID" = '091'
        test "$RUNNER_ENVIRONMENT" = github-hosted
        test "$ZERO_SPEND_MODE" = HARD
        test "$ARBM_WPS_OBSERVER" = 1
        printf '%s\\n' 'LITERAL_REMOTE_ZERO_SPEND_TASK091_ENV_PASS'
'''
IMPORT_GUARD = '''    - name: Validate observer import in pinned upstream runtime before VM
      shell: bash
      run: |
        set -euo pipefail
        test "$TASK_ID" = '091'
        (cd osworld && uv run python -c 'from desktop_env.desktop_env import DesktopEnv; assert getattr(DesktopEnv, "_arbm091_observed", False), "OBSERVER_NOT_INSTALLED"; print("PINNED_UPSTREAM_OBSERVER_IMPORT_PASS_NO_VM_STARTED")')
'''

def require(value, message):
    if not value:
        raise RuntimeError(message)

def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()

def api(endpoint, payload):
    response = subprocess.run(['gh', 'api', '--method', 'POST', f'repos/{REPO}/{endpoint}', '--input', '-'],
                              input=json.dumps(payload), text=True, capture_output=True, timeout=60)
    require(response.returncode == 0, 'GITHUB_OBJECT_UPLOAD_FAILED:' + endpoint + ':' + response.stderr[:400])
    return json.loads(response.stdout)

def replace_once(text, old, new):
    require(text.count(old) == 1, 'EXACT_REPLACEMENT_ANCHOR_CHANGED:' + old[:100])
    return text.replace(old, new, 1)

def run_tests(name, args, expected_success=True):
    result = subprocess.run(args, text=True, capture_output=True, timeout=180)
    output = result.stdout + result.stderr
    (TEMP / name).write_text(output)
    print(output, flush=True)
    if expected_success:
        require(result.returncode == 0, 'REGRESSION_FAILED:' + name)
    else:
        require(result.returncode == 1 and 'FAILED (failures=3)' in output,
                'HISTORICAL_BUG_NOT_REPRODUCED_WITH_EXACT_THREE_WORKFLOW_FAILURES')
    return result.returncode

def main():
    require(os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted', 'REMOTE_RUNNER_REQUIRED')
    require(os.environ.get('ZERO_SPEND_MODE') == 'HARD', 'ZERO_SPEND_HARD_REQUIRED')
    require(os.environ.get('GITHUB_REPOSITORY') == REPO, 'REPOSITORY_MISMATCH')
    require(git('rev-parse', 'HEAD') == SOURCE, 'SOURCE_HEAD_CHANGED')
    require(git('rev-parse', SOURCE + '^') == PARENT, 'CLEAN_PARENT_CHANGED')
    require(git('rev-list', '--count', BASE + '..HEAD') == '3', 'INITIAL_THREE_COMMITS_REQUIRED')
    require(not git('status', '--porcelain=v1', '--untracked-files=all'), 'DIRTY_INITIAL_WORKSPACE')
    require(git('ls-remote', 'origin', 'refs/heads/master').split()[0] == BASE, 'MASTER_MOVED')
    original = pathlib.Path(WORKFLOW).read_text()
    require(git('rev-parse', f'{SOURCE}:{WORKFLOW}') == '209390802fd13144df6929bc5ccd92c09c3b30c2', 'WORKFLOW_BLOB_MISMATCH')
    require(not pathlib.Path(TEST_FILE).exists(), 'TEST_ALREADY_EXISTS')
    pathlib.Path(TEST_FILE).write_text(TESTS)
    run_tests('arbm091-env-negative-regression.log',
              ['python', '-m', 'unittest', 'discover', '-s', 'tests/arbm091', '-p', 'test_runtime_contract.py', '-v'], False)
    updated = replace_once(original, '      TASK_ID: 091\n', "      TASK_ID: '091'\n")
    updated = replace_once(updated, '    - chatgpt/arbm-091-clean-transplant-proof-20260918\n', '    - ' + BRANCH + '\n')
    updated = replace_once(updated, '    - name: Prepare pinned shim runtime\n', ENV_GUARD + '    - name: Prepare pinned shim runtime\n')
    updated = replace_once(updated, '    - name: Download pinned official VM\n', IMPORT_GUARD + '    - name: Download pinned official VM\n')
    pathlib.Path(WORKFLOW).write_text(updated)
    preserved = ['scripts/arbm091/wps_observer.py', 'scripts/arbm091/score_tracker.py',
                 'scripts/arbm091/trace_gate.py', 'scripts/arbm091/verify_transplant.py',
                 'scripts/osworld_v32_gate.py', 'scripts/osworld_v32_integrity.py',
                 'scripts/osworld_local_vlm.py', 'scripts/replay_091_local_contract.py']
    note = {'schema': 1, 'source_candidate_sha': SOURCE, 'reused_second_commit': PARENT,
            'base_sha': BASE, 'failed_run': '35347563672', 'failed_job': '105608504205',
            'failed_artifact': 10548715912,
            'failed_artifact_sha256': '0ca43bacb34ce14ea1d8122db2d0b9dbb79f8ee31f0e141ef9c9cc00e9dac0da',
            'root_cause': 'GitHub job received TASK_ID=91 from unquoted 091; strict observer requires literal 091',
            'runtime_error': 'OBSERVER_REMOTE_ZERO_SPEND_TASK091_REQUIRED',
            'historical_process_exit_code': 1, 'historical_official_score': None,
            'correction': 'Quote TASK_ID as a YAML string; assert environment before preparation and import actual pinned observer before VM download',
            'negative_regression': 'Original workflow must fail exactly three of ten new tests; observer restrictions remain unchanged',
            'preserved_sha256': {name: hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() for name in preserved},
            'workflow_before_sha256': hashlib.sha256(original.encode()).hexdigest(),
            'workflow_after_sha256': hashlib.sha256(updated.encode()).hexdigest(),
            'test_sha256': hashlib.sha256(TESTS.encode()).hexdigest(),
            'remote_refs_modified_by_builder': False, 'zero_spend_mode': 'HARD', 'heavy_local': 0}
    pathlib.Path(AUDIT_FILE).write_text(json.dumps(note, indent=2, sort_keys=True) + '\n')
    manifest = json.loads(pathlib.Path(MANIFEST).read_text())
    require(isinstance(manifest, list) and len(manifest) == 107, 'INITIAL_SCOPE_CHANGED')
    manifest = sorted(set(manifest) | {TEST_FILE, AUDIT_FILE})
    require(len(manifest) == 109, 'NEW_SCOPE_MISMATCH')
    pathlib.Path(MANIFEST).write_text(json.dumps(manifest, indent=2) + '\n')
    subprocess.run(['git', 'add', '--', *sorted(ALLOWED)], check=True)
    require(set(git('diff', '--cached', '--name-only').splitlines()) == ALLOWED, 'PATCH_SCOPE_MISMATCH')
    subprocess.run(['git', 'diff', '--cached', '--check'], check=True)
    (TEMP / 'arbm091-env-fix.patch').write_text(git('diff', '--cached') + '\n')
    expected_tree = git('write-tree')
    entries = []
    for name in sorted(ALLOWED):
        data = pathlib.Path(name).read_bytes()
        blob = api('git/blobs', {'content': base64.b64encode(data).decode(), 'encoding': 'base64'})['sha']
        mode, expected_blob, _ = git('ls-files', '--stage', '--', name).split(None, 3)[:3]
        require(mode == '100644' and blob == expected_blob, 'UPLOADED_BLOB_MISMATCH:' + name)
        entries.append({'path': name, 'mode': mode, 'type': 'blob', 'sha': blob})
    tree = api('git/trees', {'base_tree': git('rev-parse', SOURCE + '^{tree}'), 'tree': entries})['sha']
    require(tree == expected_tree, 'UPLOADED_TREE_MISMATCH')
    date = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    identity = {'name': 'github-actions[bot]', 'email': '41898282+github-actions[bot]@users.noreply.github.com', 'date': date}
    commit = api('git/commits', {'message': 'fix(091): preserve literal task identity and verify observer startup before VM\n\nRebuild clean third commit; preserve first two commits, all original tests and strict gates.',
                               'tree': tree, 'parents': [PARENT], 'author': identity, 'committer': identity})
    sha = commit['sha']
    require(len(sha) == 40, 'INVALID_COMMIT_SHA')
    subprocess.run(['git', 'fetch', '--no-tags', 'origin', sha], check=True)
    require(git('rev-parse', 'FETCH_HEAD') == sha, 'FETCHED_CANDIDATE_MISMATCH')
    subprocess.run(['git', 'checkout', '--detach', sha], check=True)
    require(not git('status', '--porcelain=v1', '--untracked-files=all'), 'CANDIDATE_WORKSPACE_NOT_CLEAN')
    require(git('rev-parse', 'HEAD^') == PARENT, 'FIRST_TWO_COMMITS_CHANGED')
    require(set(git('diff', '--name-only', SOURCE, 'HEAD').splitlines()) == ALLOWED, 'FINAL_DELTA_SCOPE_CHANGED')
    subprocess.run(['git', 'diff', '--check', BASE, 'HEAD'], check=True)
    run_tests('arbm091-env-transplant.log', ['python', '-m', 'arbm091.verify_transplant'])
    run_tests('arbm091-env-proof-tests.log', ['python', '-m', 'unittest', 'discover', '-s', 'tests/arbm091', '-p', 'test_*.py', '-v'])
    run_tests('arbm091-env-original-tests.log', ['python', '-m', 'unittest', 'discover', '-s', 'scripts', '-p', 'test_osworld_*.py'])
    run_tests('arbm091-env-v32.log', ['python', 'scripts/osworld_v32_regression_gate.py'])
    require(not git('status', '--porcelain=v1', '--untracked-files=all'), 'POST_TEST_WORKSPACE_NOT_CLEAN')
    require(git('ls-remote', 'origin', 'refs/heads/master').split()[0] == BASE, 'MASTER_MOVED_DURING_PREPARATION')
    receipt = {'candidate_sha': sha, 'tree_sha': tree, 'branch': BRANCH, 'base_sha': BASE,
               'parent_sha': PARENT, 'source_candidate_sha': SOURCE, 'new_commits': 3,
               'changed_files': 109, 'correction_files': sorted(ALLOWED),
               'status': 'CLEAN_ENV_CONTRACT_CANDIDATE_TESTED_NOT_OFFICIAL_SCORE',
               'official_score': None, 'refs_modified': False, 'merged': False,
               'builder_run_id': os.environ['GITHUB_RUN_ID'], 'zero_spend_mode': 'HARD', 'heavy_local': 0}
    (TEMP / 'arbm091-env-candidate-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt), flush=True)

if __name__ == '__main__':
    main()
