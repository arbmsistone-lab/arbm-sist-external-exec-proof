"""Wire the pinned upstream volume API and verify real guest capacity."""
import json
import logging
import os
import struct
from pathlib import Path
import urllib.request

LOG = logging.getLogger(__name__)
GUEST_CAPACITY = "import json,os;f=os.statvfs('/');print(json.dumps(dict(filesystem_bytes=f.f_blocks*f.f_frsize,available_bytes=f.f_bavail*f.f_frsize,free_inodes=f.f_favail)))"


def verify_volume(server, requested_gb):
    request = urllib.request.Request(server.rstrip('/') + '/setup/execute',
        data=json.dumps({'command':['python3','-c',GUEST_CAPACITY],'shell':False,'timeout':30}).encode(),
        headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(request,timeout=60) as response: result=json.loads(response.read())
    if result.get('returncode') != 0 or result.get('status') != 'success': raise RuntimeError('VM_VOLUME_COMMAND_FAILED:' + json.dumps(result))
    capacity = json.loads(result['output'])
    LOG.info('VM_VOLUME_ACTUAL %s',json.dumps(capacity,sort_keys=True))
    # ext4 metadata consumes some advertised disk size; require actual growth.
    if capacity['filesystem_bytes'] < (requested_gb - 2) * 1024**3 or capacity['available_bytes'] < 8 * 1024**3 or capacity['free_inodes'] < 1000:
        raise RuntimeError('VM_VOLUME_NOT_EXPANDED:' + json.dumps(capacity))
    return capacity


def verify_image_capacity(path, requested_gb):
    # QCOW2's virtual size is the big-endian uint64 at offset 24. Read only
    # the header; never resize or otherwise mutate the pinned image base.
    with open(path,'rb') as image: header=image.read(32)
    if len(header)!=32 or header[:4]!=b'QFI\xfb': raise RuntimeError('INVALID_QCOW_HEADER')
    actual=struct.unpack('>Q',header[24:32])[0]
    if actual!=requested_gb*1024**3: raise RuntimeError('PINNED_IMAGE_VIRTUAL_CAPACITY_MISMATCH:'+str(actual))
    print('PINNED_IMAGE_VIRTUAL_BYTES='+str(actual))


def patch_volume(root):
    root = Path(root)
    run = root / 'scripts/python/run_multienv.py'
    text = run.read_text()
    needle = '            client_password=args.client_password,\n'
    if text.count(needle) != 1: raise RuntimeError('UPSTREAM_DESKTOP_ENV_CONSTRUCTOR_CHANGED')
    text = text.replace(needle, '            volume_size=int(os.environ["ARBM_VM_VOLUME_GB"]),\n' + needle,1)
    run.write_text(text)
    provider = root / 'desktop_env/providers/docker/provider.py'
    text = provider.read_text()
    needle = '            client_password=client_password,\n        )\n'
    if text.count(needle) != 1: raise RuntimeError('UPSTREAM_DOCKER_VOLUME_HOOK_CHANGED')
    text = text.replace(needle,needle + '        from desktop_env.providers.docker.arbm_volume import verify_volume\n'
        '        verify_volume(setup_controller.http_server, int(volume_size))\n',1)
    provider.write_text(text)
    provider.with_name('arbm_volume.py').write_text(Path(__file__).read_text())


if __name__ == '__main__':
    import sys
    if sys.argv[1]=='--check-image':
        verify_image_capacity(sys.argv[2],int(os.environ['ARBM_VM_VOLUME_GB']))
        sys.exit(0)
    patch_volume(sys.argv[1])
    print('OSWORLD_UPSTREAM_VOLUME_API_WIRED')
