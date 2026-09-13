import unittest

from osworld_v32_preflight import binary_token


class PreflightBinaryTests(unittest.TestCase):
    def test_accepts_semantic_binary_punctuation(self):
        self.assertEqual(binary_token('NO'), 'NO')
        self.assertEqual(binary_token('No.'), 'NO')
        self.assertEqual(binary_token(' yes! '), 'YES')

    def test_rejects_non_binary_explanation(self):
        self.assertEqual(binary_token('No, because the image is different.'), '')
        self.assertEqual(binary_token('maybe'), '')


if __name__ == '__main__':
    unittest.main()
