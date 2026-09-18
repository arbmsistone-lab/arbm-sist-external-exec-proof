import os
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import osworld_local_text_review as local_review


class FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return list(range(len(str(text).split())))

    def decode(self, ids, skip_special_tokens=True):
        return 'TOKENS_' + str(len(ids))


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
        self.assertEqual(local_review._token_limit(9999), 192)
        self.assertEqual(local_review._token_limit('bad'), 160)

    def test_prompt_token_limit_is_bounded(self):
        with mock.patch.dict(os.environ, {'ARBM_LOCAL_TEXT_PROMPT_TOKENS': '1'}):
            self.assertEqual(local_review._prompt_token_limit(), 512)
        with mock.patch.dict(os.environ, {'ARBM_LOCAL_TEXT_PROMPT_TOKENS': '99999'}):
            self.assertEqual(local_review._prompt_token_limit(), 3072)
        with mock.patch.dict(os.environ, {'ARBM_LOCAL_TEXT_PROMPT_TOKENS': 'bad'}):
            self.assertEqual(local_review._prompt_token_limit(), 2048)

    def test_post_focal_messages_end_with_decision_schema(self):
        system = ('BASE\nROLE=state_machine\nSPECIALTY=state machine review\n'
                  'CURRENT CANDIDATE CONTRACT (source excerpts):\n' + 'code ' * 1000)
        messages, prefix = local_review._post_focal_messages(FakeTokenizer(), system, 'evidence ' * 1000)
        self.assertEqual(prefix, '{"role":"state_machine","verdict":"')
        self.assertIn('DECIDE NOW', messages[1]['content'])
        self.assertTrue(messages[1]['content'].rstrip().endswith('Choose the verdict from evidence; PASS is not required.'))
        self.assertIn('TOKEN-BOUNDED MIDDLE OMITTED', messages[1]['content'])

    def test_post_focal_requires_explicit_role(self):
        messages, prefix = local_review._post_focal_messages(FakeTokenizer(), 'NO ROLE', 'evidence')
        self.assertIsNone(messages)
        self.assertEqual(prefix, '')

    def test_only_pinned_allowlisted_models_exist(self):
        self.assertEqual(set(local_review.MODELS), {'qwen_local', 'smollm_local'})
        for model, revision in local_review.MODELS.values():
            self.assertTrue(model)
            self.assertEqual(len(revision), 40)

    def test_cache_clear_releases_all_references(self):
        local_review._RUNTIME_CACHE['qwen_local'] = (object(), object())
        local_review.clear_runtime_cache()
        self.assertEqual(len(local_review._RUNTIME_CACHE), 0)

    def test_source_uses_eval_inference_cache_and_no_paid_route(self):
        source = pathlib.Path(local_review.__file__).read_text(encoding='utf-8')
        self.assertIn('model.eval()', source)
        self.assertIn('torch.inference_mode()', source)
        self.assertIn('use_cache=True', source)
        self.assertIn("'mandatory_cost_usd': 0", source)
        self.assertIn("'paid_fallback_used': False", source)
        self.assertIn("'post_focal_compact_prompt': post_focal", source)
        self.assertIn("'json_prefix_used': bool(prefix)", source)
        self.assertNotIn('cuda()', source)
        self.assertNotIn('.to(\'cuda\')', source)

    def test_lru_cache_is_explicitly_bounded_before_insert(self):
        source = pathlib.Path(local_review.__file__).read_text(encoding='utf-8')
        self.assertIn('while len(_RUNTIME_CACHE) >= limit:', source)
        self.assertIn('_RUNTIME_CACHE.popitem(last=False)', source)


if __name__ == '__main__':
    unittest.main()
