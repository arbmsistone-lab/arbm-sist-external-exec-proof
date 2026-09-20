import json
import unittest
import struct
import tempfile
from unittest.mock import patch
from osworld_docker_volume import verify_volume, verify_image_capacity, GUEST_CAPACITY


class VolumeTests(unittest.TestCase):
    def response(self, capacity, **extra):
        return (200, {'status':'success','returncode':0,'output':json.dumps(capacity),**extra}, {})

    def test_actual_capacity_required(self):
        for capacity in ({'filesystem_bytes':62*1024**3,'available_bytes':10*1024**3,'free_inodes':10000},
                         {'filesystem_bytes':30*1024**3,'available_bytes':10*1024**3,'free_inodes':10000},
                         {'filesystem_bytes':62*1024**3,'available_bytes':0,'free_inodes':10000}):
            with patch('osworld_docker_volume.request_json',return_value=self.response(capacity)):
                if capacity['filesystem_bytes'] > 60*1024**3 and capacity['available_bytes']:
                    self.assertEqual(verify_volume('http://guest',64),capacity)
                else:
                    with self.assertRaisesRegex(RuntimeError,'NOT_EXPANDED'): verify_volume('http://guest',64)

    def test_http200_nonzero_command_is_failure(self):
        with patch('osworld_docker_volume.request_json',return_value=self.response({},returncode=1)):
            with self.assertRaisesRegex(RuntimeError,'COMMAND_FAILED'): verify_volume('http://guest',64)

    def test_guest_probe_has_no_mutation(self):
        compile(GUEST_CAPACITY,'<capacity>','exec')
        self.assertNotIn('unlink',GUEST_CAPACITY)

    def test_actual_pinned_image_capacity(self):
        with tempfile.NamedTemporaryFile(delete=False) as image:
            path=image.name
            image.write(b'QFI\xfb'+bytes(20)+struct.pack('>Q',50*1024**3))
        try:
            verify_image_capacity(path,50)
            with self.assertRaisesRegex(RuntimeError,'CAPACITY_MISMATCH'): verify_image_capacity(path,64)
        finally:
            import os
            os.unlink(path)


if __name__ == '__main__': unittest.main()
