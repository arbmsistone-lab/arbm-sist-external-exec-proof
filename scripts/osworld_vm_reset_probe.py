"""Real cloud-only Docker reset regression; never benchmark score evidence."""
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile
import uuid

from osworld_docker_volume import verify_volume
from osworld_evidence import seal
from osworld_vm_upload import upload, vm_execute


def file_sha(path):
    with open(path, 'rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def main(image, evidence):
    if (os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted' or
            os.environ.get('GITHUB_ACTIONS') != 'true' or
            os.environ.get('ZERO_SPEND_MODE') != 'HARD'):
        raise RuntimeError('CLOUD_ONLY_HARD_MODE_REQUIRED')
    from desktop_env.desktop_env import DesktopEnv
    evidence.mkdir(parents=True, exist_ok=True)
    proof = {'purpose': 'cloud upload/reset integration only; not an official task score',
             'candidate_sha': os.environ['GITHUB_SHA'], 'zero_spend_mode': 'HARD',
             'heavy_local': 0, 'status': 'NOT PROVEN'}
    base_before = file_sha(image)
    env = None
    try:
        env = DesktopEnv(provider_name='docker', path_to_vm=str(image), headless=True,
                         require_a11y_tree=False, volume_size=50)
        server = env.setup_controller.http_server
        before_capacity = verify_volume(server, 50)
        boot_before = vm_execute(server, ['python3', '-c',
            "import json;print(json.dumps(dict(boot_id=open('/proc/sys/kernel/random/boot_id').read().strip())))"])
        guest_dir = '/home/user/.arbm-reset-probe-' + uuid.uuid4().hex
        receipts = []
        with tempfile.TemporaryDirectory(prefix='arbm-reset-fixtures-') as directory:
            for size in (0, 257, 4 * 1024 * 1024):
                source = Path(directory) / ('fixture-' + str(size))
                source.write_bytes((bytes(range(256)) * ((size + 255) // 256))[:size])
                destination = guest_dir + '/' + source.name
                first = upload(server, source, destination)
                repeated = upload(server, source, destination)
                receipts.append({'destination': destination, 'size': size,
                    'host_sha256': file_sha(source), 'first': first, 'repeated': repeated})
        # WAIT is an upstream public step: it marks the used environment dirty.
        # No task class, evaluator, benchmark asset, or scoring path is involved.
        env.step('WAIT', pause=0)
        env.reset(None)
        server = env.setup_controller.http_server
        after_capacity = verify_volume(server, 50)
        reset = vm_execute(server, ['python3', '-c',
            "import json,os,sys;print(json.dumps(dict(boot_id=open('/proc/sys/kernel/random/boot_id').read().strip(),owned_fixture_directory_exists=os.path.lexists(sys.argv[1]))))",
            guest_dir])
        if reset['owned_fixture_directory_exists'] or reset['boot_id'] == boot_before['boot_id']:
            raise RuntimeError('OFFICIAL_RESET_DID_NOT_REVERT_OWNED_FIXTURES')
        proof.update(status='CLOUD_UPLOAD_RESET_PASS', before_capacity=before_capacity,
            after_capacity=after_capacity, boot_before=boot_before, reset=reset,
            upload_receipts=receipts)
    finally:
        if env is not None:
            env.close()
        base_after = file_sha(image)
        proof.update(qcow_base_before=base_before, qcow_base_after=base_after)
        if base_before != base_after:
            proof['status'] = 'NOT PROVEN'
            proof['failure'] = 'PINNED_QCOW_BASE_MODIFIED'
        (evidence / 'reset-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
        seal(evidence)
        if base_before != base_after:
            raise RuntimeError('PINNED_QCOW_BASE_MODIFIED')
    print(json.dumps(proof))


if __name__ == '__main__':
    import sys
    logging.basicConfig(level=logging.INFO)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
