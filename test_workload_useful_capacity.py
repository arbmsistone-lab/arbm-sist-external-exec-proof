import unittest
import workload_useful_capacity as w

class WorkloadUsefulCapacityTests(unittest.TestCase):
    def test_valid_short_json_lane(self):
        r=w.qualifies(1024,102,"short_json")
        self.assertEqual(r["status"],"PASS")
        self.assertTrue(r["count_as_concise_capacity"])

    def test_rejects_long_output(self):
        self.assertEqual(w.qualifies(2000,103,"decision")["status"],"REJECT_TO_LONG_LANE")

    def test_rejects_short_prompt(self):
        self.assertEqual(w.qualifies(1023,50,"routing")["status"],"REJECT_TO_LONG_LANE")

    def test_live_sample_must_obey_contract(self):
        r=w.live_sample_valid(6330,73,102)
        self.assertEqual(r["status"],"PASS")
        self.assertEqual(r["useful_tokens"],6403)

if __name__=='__main__': unittest.main()
