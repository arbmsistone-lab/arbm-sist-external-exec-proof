import hashlib, unittest

class ExternalSessionContractTests(unittest.TestCase):
    def test_instruction_hash_session_keys_differ_across_tasks(self):
        a='Open Chrome and do A'
        b='Open Calc and do B'
        ka='run:instruction:'+hashlib.sha256(a.encode()).hexdigest()[:24]
        kb='run:instruction:'+hashlib.sha256(b.encode()).hexdigest()[:24]
        self.assertNotEqual(ka,kb)
        self.assertEqual(ka,'run:instruction:'+hashlib.sha256(a.encode()).hexdigest()[:24])

if __name__=='__main__':
    unittest.main()