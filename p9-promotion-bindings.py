"""Bind execution capacity without changing tests, scope or protected policy."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, 'harness-src')
from harness.e2e.repo_config_binding import resolve_repo_config
from harness.e2e.runtime_policy_binding import resolve_runtime_policy

assert os.environ['GITHUB_REPOSITORY'] == 'arbmsistone-lab/arbm-sist-external-exec-proof'
assert os.environ['RUNNER_ENVIRONMENT'] == 'github-hosted'
assert os.environ['ZERO_SPEND_MODE'] == 'HARD'
assert os.environ['ARBM_ALLOW_LOCAL_AI'] == '0'
root = Path('data') / os.environ['REPO_ID']
out = Path('p9-bindings')
out.mkdir(exist_ok=True)
p = root / 'metadata.json'
raw = p.read_bytes()
before = json.loads(raw)
available = int(subprocess.check_output(['docker', 'info', '--format', '{{.NCPU}}'], text=True))
requested = before.get('docker_cpus', 16)
assert available > 0 and isinstance(requested, (int, float)) and requested > 0
effective = dict(before, docker_cpus=min(requested, available))
assert {k:v for k,v in before.items() if k != 'docker_cpus'} == {k:v for k,v in effective.items() if k != 'docker_cpus'}
p.write_text(json.dumps(effective, indent=2)+'\n')
(out/'metadata-original.json').write_bytes(raw)
(out/'metadata-effective.json').write_bytes(p.read_bytes())
(out/'runtime-capacity.json').write_text(json.dumps({'requested':requested, 'available':available, 'effective':effective['docker_cpus'], 'changed_fields':['docker_cpus'], 'original_sha256':hashlib.sha256(raw).hexdigest(), 'effective_sha256':hashlib.sha256(p.read_bytes()).hexdigest()}, indent=2)+'\n')
rc = resolve_repo_config(os.environ['REPO_ID'], root, project_root=Path('harness-src'))
rp = resolve_runtime_policy(os.environ['REPO_ID'], Path('harness-src'), unprotected=False)
assert hashlib.sha256(rc.raw_bytes).hexdigest() == 'ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356'
rp_sha = hashlib.sha256(rp.raw_bytes).hexdigest()
assert rp_sha == 'aa7ec051587f229ac4ac9d3822f2b90790cac551f61a1c284d5664ad45728f1f'
assert rp.mode == 'protected'
(Path('data/config')/(os.environ['REPO_ID']+'.yaml')).write_bytes(rc.raw_bytes)
(out/'repo_config.yaml').write_bytes(rc.raw_bytes)
(out/'runtime_policy.yaml').write_bytes(rp.raw_bytes)
with open(os.environ['GITHUB_ENV'], 'a') as f:
    f.write('RUNTIME_POLICY_SHA256='+rp_sha+'\n')
print('PINNED_BINDINGS_AND_CAPACITY=PASS')
