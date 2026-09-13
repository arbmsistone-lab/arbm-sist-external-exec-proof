"""Verified single-copy upload through the existing official execute endpoint.

No multipart spool, shell interpolation, task IDs or evaluator changes. Retries
write at a verified offset, so a lost acknowledgement cannot duplicate bytes.
"""
import base64
import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

LOG = logging.getLogger(__name__)
CHUNK_BYTES = 64 * 1024  # encoded argv stays below Linux's per-argument limit
RESERVE_BYTES = 64 * 1024 * 1024

GUEST = r'''
import base64, errno, fcntl, hashlib, json, os, stat, sys
mode, path, token, size, expected, offset, encoded = sys.argv[1:]
size, offset = int(size), int(offset)
assert os.path.isabs(path) and os.path.basename(path), 'ABSOLUTE_DESTINATION_REQUIRED'
parent = os.path.dirname(path)
os.makedirs(parent, exist_ok=True)
marker = path + '.arbm-upload-state'
flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
with os.fdopen(os.open(marker, flags, 0o600), 'r+') as state:
    fcntl.flock(state, fcntl.LOCK_EX)
    assert stat.S_ISREG(os.fstat(state.fileno()).st_mode), 'UNSAFE_STATE_FILE'
    raw = state.read()
    current = json.loads(raw) if raw else {}
    if os.path.lexists(path):
        assert stat.S_ISREG(os.lstat(path).st_mode), 'UNSAFE_DESTINATION'
    def save(value):
        state.seek(0); state.truncate(); json.dump(value, state); state.flush(); os.fsync(state.fileno())
    def digest():
        h = hashlib.sha256()
        with open(path, 'rb') as src:
            for block in iter(lambda: src.read(1024 * 1024), b''): h.update(block)
        return h.hexdigest()
    if mode == 'begin':
        if os.path.isfile(path) and os.path.getsize(path) == size and digest() == expected:
            print(json.dumps({'complete': True, 'sha256': expected, 'size': size}))
        else:
            fs = os.statvfs(parent)
            available = fs.f_bavail * fs.f_frsize
            allocated = os.stat(path).st_blocks * 512 if os.path.isfile(path) else 0
            diagnostics = {'destination': path, 'required_bytes': size, 'available_bytes': available,
                           'reclaimable_destination_bytes': allocated, 'reserve_bytes': 67108864,
                           'filesystem_bytes': fs.f_blocks * fs.f_frsize, 'free_inodes': fs.f_favail,
                           'multipart_attempted': False}
            if available + allocated < size + 67108864 or fs.f_favail < 16:
                # Diagnose before any truncation. Never delete unknown VM files.
                import subprocess
                diagnostics['disk_usage'] = subprocess.run(['du','-x','-h','--max-depth=2',
                    '/home/user/.cache','/home/user/.local/share/flatpak','/var/tmp','/tmp'],
                    capture_output=True, text=True, timeout=60).stdout[-12000:]
                raise OSError(errno.ENOSPC, 'VM_UPLOAD_PREFLIGHT:' + json.dumps(diagnostics))
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o644)
            inode = os.fstat(fd).st_ino
            os.close(fd)
            save({'token': token, 'inode': inode, 'size': size, 'sha256': expected})
            print(json.dumps(diagnostics))
    else:
        assert current.get('token') == token and current.get('sha256') == expected, 'UPLOAD_SESSION_CHANGED'
        if mode == 'abort' and current.get('aborted'):
            print(json.dumps({'aborted': True})); sys.exit(0)
        assert os.stat(path).st_ino == current['inode'], 'UPLOAD_DESTINATION_CHANGED'
        if mode == 'chunk':
            block = base64.b64decode(encoded, validate=True)
            assert 0 < len(block) <= 65536 and offset + len(block) <= size, 'UPLOAD_CHUNK_RANGE'
            with os.fdopen(os.open(path, os.O_RDWR | os.O_NOFOLLOW), 'r+b') as dst:
                length = os.fstat(dst.fileno()).st_size
                assert offset <= length <= offset + len(block), 'UPLOAD_OFFSET_MISMATCH'
                dst.seek(offset)
                previous = dst.read(len(block))
                assert block.startswith(previous), 'UPLOAD_RETRY_BYTES_MISMATCH'
                dst.seek(offset)
                dst.write(block); dst.truncate(offset + len(block)); dst.flush(); os.fsync(dst.fileno())
            print(json.dumps({'offset': offset + len(block)}))
        elif mode == 'finish':
            actual = digest()
            assert os.path.getsize(path) == size and actual == expected, 'UPLOAD_SHA256_MISMATCH:' + actual
            save({'token': token, 'inode': current['inode'], 'size': size, 'sha256': expected, 'complete': True})
            print(json.dumps({'complete': True, 'sha256': actual, 'size': size}))
        elif mode == 'abort':
            # Remove only the partial destination proven to belong to this session.
            if not current.get('complete'): os.unlink(path)
            save({'token': token, 'sha256': expected, 'aborted': True})
            print(json.dumps({'aborted': True}))
        else: raise ValueError('UNKNOWN_UPLOAD_OPERATION')
'''


class UploadError(RuntimeError):
    pass


def vm_execute(server, command):
    request = urllib.request.Request(server.rstrip('/') + '/setup/execute',
        data=json.dumps({'command': command, 'shell': False, 'timeout': 120}).encode(),
        headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=180) as response:
        data = json.loads(response.read())
    if data.get('status') != 'success' or data.get('returncode') != 0:
        raise UploadError('VM_UPLOAD_COMMAND_FAILED:' + json.dumps(data))
    return json.loads(data.get('output', ''))


def upload(server, source, destination, execute=None, sleep=time.sleep):
    source = Path(source)
    size = source.stat().st_size
    h = hashlib.sha256()
    with source.open('rb') as src:
        for block in iter(lambda: src.read(1024 * 1024), b''): h.update(block)
    expected = h.hexdigest()
    token = uuid.uuid4().hex
    execute = execute or (lambda command: vm_execute(server, command))

    def call(mode, offset=0, block=b''):
        command = ['python3', '-c', GUEST, mode, destination, token, str(size), expected,
                   str(offset), base64.b64encode(block).decode('ascii')]
        for attempt in range(3):
            try:
                return execute(command)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                if isinstance(exc, urllib.error.HTTPError) and exc.code not in (500, 502, 503, 504): raise
                if attempt == 2: raise
                LOG.warning('VM_UPLOAD_RETRY mode=%s offset=%s attempt=%s error=%s',
                            mode, offset, attempt + 1, type(exc).__name__)
                sleep(attempt + 1)

    begun = False
    try:
        info = call('begin')
        LOG.info('VM_UPLOAD_PREFLIGHT %s', json.dumps(info, sort_keys=True))
        if not info.get('complete'):
            begun = True
            offset = 0
            with source.open('rb') as src:
                while block := src.read(CHUNK_BYTES):
                    ack = call('chunk', offset, block)
                    offset += len(block)
                    if ack.get('offset') != offset: raise UploadError('VM_UPLOAD_BAD_ACK')
            info = call('finish')
        if info.get('complete') is not True or info.get('sha256') != expected or info.get('size') != size:
            raise UploadError('VM_UPLOAD_SHA256_MISMATCH')
    except Exception as exc:
        if begun:
            try: call('abort')
            except Exception as cleanup:
                raise UploadError(f'VM_UPLOAD_FAILED:{exc}; PARTIAL_CLEANUP_FAILED:{cleanup}') from exc
        raise
    LOG.info('VM_UPLOAD_VERIFIED destination=%s bytes=%s sha256=%s multipart_attempted=false',
             destination, size, expected)
    return info


def patch_setup(path):
    """Replace only transport in the hash-pinned upstream download method."""
    path = Path(path)
    text = path.read_text(encoding='utf-8')
    start = text.index('            form = MultipartEncoder({', text.index('    def _download_setup('))
    end = text.index('    def _upload_file_setup(', start)
    old = text[start:end]
    if old.count('/upload') != 2 or 'timeout=600' not in old:
        raise UploadError('UPSTREAM_UPLOAD_TRANSPORT_CHANGED')
    text = text[:start] + ('            from desktop_env.controllers.arbm_vm_upload import upload\n'
                         '            upload(self.http_server, cache_path, path)\n\n') + text[end:]
    path.write_text(text, encoding='utf-8')
    path.with_name('arbm_vm_upload.py').write_text(Path(__file__).read_text(encoding='utf-8'), encoding='utf-8')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('setup_path')
    patch_setup(parser.parse_args().setup_path)
    print('OSWORLD_SINGLE_COPY_UPLOAD_PATCH_APPLIED')
