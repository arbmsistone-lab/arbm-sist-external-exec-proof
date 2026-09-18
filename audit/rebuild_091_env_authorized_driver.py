"""Separate authorized workflow publication from restricted CI object assembly.

The ARBM connector already wrote the reviewed workflow on a staging branch.
This driver verifies that commit and prevents CI from submitting workflow edits.
It never updates a remote reference, permission, token or protected branch.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess

STAGED = '7caaadf6da13665fe77c80e7e103162ff2a6d6d8'
WORKFLOW_BLOB = '7b2b66937cf6b986a54067063ad8cdc91212846d'
WORKFLOW_SHA256 = '5fd49cdec9b9dd9a89eed7afbf862c7df1bdcf454e246abbf243f2858d70cd4b'
BUILDER_BLOB = '3373229ef12e0177dc77d20ab35ccbd906800e54'
source = Path(__file__).with_name('rebuild_091_env_contract.py')
raw = source.read_bytes()
assert hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == BUILDER_BLOB, 'REVIEWED_BUILDER_CHANGED'
spec = importlib.util.spec_from_file_location('reviewed_builder', source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.require(os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted', 'REMOTE_RUNNER_REQUIRED')
module.require(os.environ.get('ZERO_SPEND_MODE') == 'HARD', 'ZERO_SPEND_HARD_REQUIRED')
subprocess.run(['git', 'fetch', '--no-tags', 'origin', STAGED], check=True)
module.require(module.git('rev-parse', STAGED + '^') == module.SOURCE, 'AUTHORIZED_STAGING_PARENT_CHANGED')
module.require(module.git('diff', '--name-only', module.SOURCE, STAGED) == module.WORKFLOW, 'AUTHORIZED_STAGING_SCOPE_CHANGED')
module.require(module.git('rev-parse', f'{STAGED}:{module.WORKFLOW}') == WORKFLOW_BLOB, 'AUTHORIZED_WORKFLOW_BLOB_CHANGED')
workflow = subprocess.check_output(['git', 'show', f'{STAGED}:{module.WORKFLOW}'])
module.require(hashlib.sha256(workflow).hexdigest() == WORKFLOW_SHA256, 'AUTHORIZED_WORKFLOW_BYTES_CHANGED')
base_tree = module.git('rev-parse', STAGED + '^{tree}')
original_api = module.api
created_tree = None

def scoped_api(endpoint, payload):
    global created_tree
    if endpoint == 'git/trees':
        module.require(payload['base_tree'] == module.git('rev-parse', module.SOURCE + '^{tree}'), 'UNEXPECTED_TREE_BASE')
        entries = payload['tree']
        module.require({row['path'] for row in entries} == module.ALLOWED, 'UNEXPECTED_TREE_SCOPE')
        existing = [row for row in entries if row['path'] == module.WORKFLOW]
        module.require(len(existing) == 1 and existing[0]['sha'] == WORKFLOW_BLOB, 'WORKFLOW_NOT_PREAUTHORIZED')
        non_workflow = [row for row in entries if row['path'] != module.WORKFLOW]
        module.require(len(non_workflow) == 3 and all(not row['path'].startswith('.github/') for row in non_workflow), 'CI_WORKFLOW_WRITES_FORBIDDEN')
        result = original_api(endpoint, {'base_tree': base_tree, 'tree': non_workflow})
        created_tree = result['sha']
        return result
    if endpoint == 'git/commits':
        module.require(created_tree is not None and payload['tree'] == created_tree, 'UNVERIFIED_COMMIT_TREE')
        module.require(payload['parents'] == [module.PARENT], 'CLEAN_COMMIT_PARENT_CHANGED')
    else:
        module.require(endpoint == 'git/blobs', 'UNSUPPORTED_WRITE_ENDPOINT')
    return original_api(endpoint, payload)

module.api = scoped_api
Path(os.environ['RUNNER_TEMP'], 'arbm091-env-workflow-authorization.log').write_text(json.dumps({
    'authorized_staging_commit': STAGED, 'workflow_blob': WORKFLOW_BLOB,
    'workflow_sha256': WORKFLOW_SHA256, 'ci_workflow_tree_entries': 0,
    'refs_modified': False, 'permissions_changed': False,
    'status': 'VERIFIED_PREAUTHORIZED_WORKFLOW_REUSE_NOT_TASK_PROOF'
}, indent=2) + '\n')
module.main()
