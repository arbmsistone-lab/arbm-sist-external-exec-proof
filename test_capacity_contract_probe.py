import unittest
import capacity_contract_probe as c

class ContractProbeTests(unittest.TestCase):
    def test_all_expected_contract_terms_pass(self):
        pages={url:' '.join(needles) for _,(url,needles) in c.CHECKS.items()}
        out=c.probe(lambda url:(200,pages[url]))
        self.assertEqual(out['status'],'PASS')
    def test_missing_term_fails_closed(self):
        out=c.probe(lambda url:(200,'changed contract'))
        self.assertEqual(out['status'],'FAIL')
        self.assertTrue(all(x['status']=='DRIFT' for x in out['checks']))
    def test_unreachable_fails_closed(self):
        def boom(url): raise TimeoutError()
        out=c.probe(boom)
        self.assertEqual(out['status'],'FAIL')

if __name__=='__main__': unittest.main()
