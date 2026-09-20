import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import urllib.error
from osworld_vm_upload import upload, GUEST, UploadError, patch_setup


@unittest.skipUnless(os.name == 'posix', 'Official guest integration runs on Linux cloud CI')
class GuestUploadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / 'source'
        self.src.write_bytes(bytes(range(256)) * 600)
        self.dst = self.root / 'nested' / 'uploaded file'
        self.calls = []

    def execute(self, command):
        self.calls.append(command[3])
        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
        if result.returncode: raise UploadError(result.stderr)
        return json.loads(result.stdout)

    def send(self, execute=None):
        return upload('http://unused', self.src, str(self.dst), execute=execute or self.execute, sleep=lambda _: None)

    def test_small_large_empty_and_idempotent(self):
        for size in (0, 5, 153600):
            self.src.write_bytes(b'a' * size)
            info = self.send()
            self.assertEqual(self.dst.read_bytes(), self.src.read_bytes())
            self.assertEqual(info['sha256'], hashlib.sha256(self.src.read_bytes()).hexdigest())
            self.calls.clear(); self.send()
            self.assertEqual(self.calls, ['begin'])

    def test_lost_chunk_acknowledgement_and_http500(self):
        lost = False
        def execute(command):
            nonlocal lost
            result = self.execute(command)
            if command[3] == 'chunk' and not lost:
                lost = True
                raise urllib.error.HTTPError('http://unused', 500, 'lost ack', {}, None)
            return result
        self.send(execute)
        self.assertEqual(self.dst.read_bytes(), self.src.read_bytes())

    def test_interrupted_transfer_removes_only_owned_partial(self):
        other = self.root / 'unrelated'; other.write_text('keep')
        def execute(command):
            if command[3] == 'chunk': raise TimeoutError('interrupted')
            return self.execute(command)
        with self.assertRaises(TimeoutError): self.send(execute)
        self.assertFalse(self.dst.exists())
        self.assertEqual(other.read_text(), 'keep')
        self.send()
        self.assertEqual(self.dst.read_bytes(), self.src.read_bytes())

    def test_corrupted_file_fails_closed_and_cleans_partial(self):
        def execute(command):
            if command[3] == 'finish':
                with self.dst.open('r+b') as dst: dst.write(b'wrong')
            return self.execute(command)
        with self.assertRaisesRegex(UploadError, 'SHA256_MISMATCH'): self.send(execute)
        self.assertFalse(self.dst.exists())

    def test_enospc_preflight_preserves_existing_destination(self):
        self.dst.parent.mkdir(); self.dst.write_bytes(b'keep')
        def execute(command):
            command = list(command)
            command[2] = command[2].replace('fs = os.statvfs(parent)',
                "fs = type('FS', (), dict(f_bavail=0, f_frsize=4096, f_blocks=100, f_favail=10))()")
            return self.execute(command)
        with self.assertRaisesRegex(UploadError, 'VM_UPLOAD_PREFLIGHT'): self.send(execute)
        self.assertEqual(self.dst.read_bytes(), b'keep')
        self.assertEqual(self.calls, ['begin'])

    def test_enospc_during_write_is_not_retried(self):
        def execute(command):
            if command[3] == 'chunk': raise UploadError(str(OSError(errno.ENOSPC, 'disk full')))
            return self.execute(command)
        with self.assertRaisesRegex(UploadError, 'disk full'): self.send(execute)
        self.assertEqual(self.calls, ['begin', 'abort'])
        self.assertFalse(self.dst.exists())

    def test_symlink_destination_is_rejected(self):
        other = self.root / 'unrelated'; other.write_text('keep')
        self.dst.parent.mkdir(); self.dst.symlink_to(other)
        with self.assertRaisesRegex(UploadError, 'UNSAFE_DESTINATION'): self.send()
        self.assertEqual(other.read_text(), 'keep')

    def test_corrupt_ack_fails_closed(self):
        def execute(command):
            result = self.execute(command)
            return {'offset': -1} if command[3] == 'chunk' else result
        with self.assertRaisesRegex(UploadError, 'BAD_ACK'): self.send(execute)
        self.assertFalse(self.dst.exists())


class UploadContractTests(unittest.TestCase):
    def test_guest_is_valid_python_and_bounded_argv(self):
        compile(GUEST, '<guest upload>', 'exec')
        from osworld_vm_upload import CHUNK_BYTES
        self.assertLess(CHUNK_BYTES * 4 // 3 + 4, 128 * 1024)

    def test_patch_rejects_unexpected_upstream(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'setup.py'; path.write_text('changed upstream')
            with self.assertRaises(ValueError): patch_setup(path)


if __name__ == '__main__': unittest.main()
