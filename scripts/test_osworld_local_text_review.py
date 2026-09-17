import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import osworld_local_text_review as local_review


class LocalTextReviewTests(unittest.TestCase):
    def tearDown(self):
        local_review._RUNTIME_CACHE.clear()

    def test_cache_limit_is_strictly_bounded(self):
        with mock.patch.dict(os.environ, {'ARBM_LOCAL_TEXT_CACHE_MODELS': '99'}):
            self.assertEqual(local_review._cache_limit(), 2)
        with mock.patch.dict(os.environ, {'ARBM_LOCAL_TEXT_CACHE_MODELS': '-1'}):
            self.assertEqual(local_review._cache_limit(), 0)
        with mock.patch.dict(os.environ, {'ARBM_LOCAL_TEXT_CACHE_MODELS': 'bad'}):
            self.assertEqual(local_review._cache_limit(), 1)

    def test_generation_token_limit_is_bounded(self):
        self.assertEqual(local_review._token_limit(1), 16)
        self.assertEqual(local_review._token_limit(9999), 512)
        self.assertEqual(local_review._token_limit('bad'), 320)

    def test_only_pinned_allowlisted_models_exist(self):
        self.assertEqual(set(local_review.MODELS), {'qwen_local', 'smollm_local'})
        for model, revision in local_review.MODELS.values():
            self.assertTrue(model)
            self.assertEqual(len(revision), 40)

    def test_cache_clear_releases_all_references(self):
        local_review._RUNTIME_CACHE['qwen_local'] = (object(), object())
        local_review.clear_runtime_cache()
        self.assertEqual(len(local_review._RUNTIME_CACHE), 0)

    def test_source_uses_eval_inference_mode_and_no_paid_route(self):
        source = pathlib.Path(local_review.__file__).read_text(encoding='utf-8')
        self.assertIn('model.eval()', source)
        self.assertIn('torch.inference_mode()', source)
        self.assertIn("'mandatory_cost_usd': 0", source)
        self.assertIn("'paid_fallback_used': False", source)
        self.assertNotIn('cuda()', source)
        self.assertNotIn('.to(\'cuda\')', source)

    def test_lru_cache_is_explicitly_bounded_before_insert(self):
        source = pathlib.Path(local_review.__file__).read_text(encoding='utf-8')
        self.assertIn('while len(_RUNTIME_CACHE) >= limit:', source)
        self.assertIn('_RUNTIME_CACHE.popitem(last=False)', source)


if __name__ == '__main__':
    unittest.main()
