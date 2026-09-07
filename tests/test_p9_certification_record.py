import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'certification' / 'p9-dubbo-m0031-official-promotion.json'

class P9CertificationRecordTests(unittest.TestCase):
    def setUp(self):
        self.d = json.loads(RECORD.read_text(encoding='utf-8'))

    def test_official_result_is_fail_closed_green(self):
        e = self.d['officialEvaluator']
        self.assertEqual(e['exitCode'], 0)
        for key in ['resolved','promotionContractPass','promotionGrade','patchExists','patchSuccessfullyApplied','snapshotIntegrityOk']:
            self.assertIs(e[key], True, key)
        self.assertIs(e['legacySnapshot'], False)
        self.assertIs(e['infrastructureFailure'], False)
        self.assertIs(e['infraInvalid'], False)

    def test_required_scoring_is_complete(self):
        s = self.d['requiredScoring']
        self.assertEqual(s['passToPass'], {'required':6954,'achieved':6954,'failed':0,'missing':0})
        self.assertEqual(s['noneToPass'], {'required':1,'achieved':1,'missing':0})
        self.assertEqual(s['failToPass'], {'required':0,'achieved':0})
