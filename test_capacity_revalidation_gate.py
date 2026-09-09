import json, tempfile, unittest
from datetime import datetime, timezone, timedelta
import capacity_revalidation_gate as g

class RevalidationTests(unittest.TestCase):
    def test_current_evidence_passes_stronger_n2(self):
        out=g.check()
        self.assertEqual(out['status'],'PASS')
        self.assertGreaterEqual(out['chaos']['n_plus_two_floor_useful_units_per_day'],5_000_000)
    def test_stale_evidence_fails_closed(self):
        with open('account-capacity-evidence.json',encoding='utf-8') as src: d=json.load(src)
        d['observed_at']=(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()
        with tempfile.NamedTemporaryFile('w',delete=False,encoding='utf-8',suffix='.json') as f:
            json.dump(d,f); path=f.name
        out=g.check(path)
        self.assertEqual(out['status'],'FAIL')
        self.assertIn('STALE_ROOT_EVIDENCE',out['errors'])

if __name__=='__main__': unittest.main()
