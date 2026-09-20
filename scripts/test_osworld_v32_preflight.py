import unittest

from osworld_v32_preflight import binary_token, free_capacity_proven


class PreflightBinaryTests(unittest.TestCase):
    def test_accepts_semantic_binary_punctuation(self):
        self.assertEqual(binary_token('NO'), 'NO')
        self.assertEqual(binary_token('No.'), 'NO')
        self.assertEqual(binary_token(' yes! '), 'YES')

    def test_rejects_non_binary_explanation(self):
        self.assertEqual(binary_token('No, because the image is different.'), '')
        self.assertEqual(binary_token('maybe'), '')

    def test_accepts_only_proven_zero_cost_capacity(self):
        data={'provider_attempts':[{'status':200,'parsed':True,'free_plan_proven':True,
            'mandatory_cost_usd':0,'paid_fallback_used':False}]}
        self.assertTrue(free_capacity_proven(data))

    def test_rejects_unproven_or_paid_capacity(self):
        self.assertFalse(free_capacity_proven({'provider_attempts':[{'status':200,'parsed':True,
            'free_plan_proven':False,'mandatory_cost_usd':0,'paid_fallback_used':False}]}))
        self.assertFalse(free_capacity_proven({'provider_attempts':[{'status':200,'parsed':True,
            'free_plan_proven':True,'mandatory_cost_usd':1,'paid_fallback_used':True}]}))


if __name__ == '__main__':
    unittest.main()
