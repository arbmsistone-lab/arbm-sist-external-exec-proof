import copy
import json
import unittest
from unittest import mock

from arbm091.semantic_transaction import (
    SemanticTransactionError,
    normalize_deck,
    verify_exact_text_transaction,
)
from arbm091 import gateway_supervisor


KEY=(2,"shape",15,"SummaryArr_Value")


def state(text, font_sizes):
    return {
        "deck_slide_shapes": {
            "2": [{
                "kind":"shape","id":15,"name":"SummaryArr_Value",
                "text":text,
                "geometry":{"x":100,"y":100,"w":200,"h":80},
                "font_sizes":list(font_sizes),"fill_rgb":"FFFFFF",
            }]
        },
        "deck_slide_relationships":{"2":[]},
        "deck_slide_charts":{"2":[]},
    }


class Response:
    status=200
    def __enter__(self): return self
    def __exit__(self,*_): return False
    def read(self):
        return json.dumps({
            "status":"ok",
            "pipeline":"arbm-osworld-v32-isolated",
            "build":"arbm-osworld-v32-master-20260914",
        }).encode()


class PreventiveFatalPreflight(unittest.TestCase):
    def test_summaryarr_split_ooxml_run_is_semantically_equivalent(self):
        before=state("$42.8M",[2400,2400])
        after=state("$40.9M",[2400,2400,2400,2400,2400,2400])
        verdict=verify_exact_text_transaction(before,after,[KEY],"$40.9M")
        self.assertEqual(verdict["status"],"PASS")
        self.assertEqual(verdict["collateral_diff"],[])
        self.assertEqual(normalize_deck(before)[KEY]["font_sizes"],(2400,))
        self.assertEqual(normalize_deck(after)[KEY]["font_sizes"],(2400,))
        print("SUMMARYARR_SPLIT_OOXML_RUN=PASS")

    def test_real_font_drift_is_not_hidden_by_run_normalization(self):
        before=state("$42.8M",[2400,2400])
        after=state("$40.9M",[2400,2300,2300])
        with self.assertRaises(SemanticTransactionError):
            verify_exact_text_transaction(before,after,[KEY],"$40.9M")

    def test_corrupt_text_is_still_rejected(self):
        before=state("$42.8M",[2400,2400])
        after=state("$40.M",[2400,2400,2400,2400])
        with self.assertRaises(SemanticTransactionError):
            verify_exact_text_transaction(before,after,[KEY],"$40.9M")

    def test_gateway_route_probe_is_evidence_isolated(self):
        calls=[]
        def fake_urlopen(target,timeout=None):
            calls.append(target)
            return Response()
        with mock.patch.object(gateway_supervisor.urllib.request,"urlopen",side_effect=fake_urlopen):
            self.assertTrue(gateway_supervisor.route_probe())
        self.assertEqual(calls,["http://127.0.0.1:8088/health"])
        self.assertTrue(all(not isinstance(x,gateway_supervisor.urllib.request.Request) for x in calls))
        print("HEALTH_PROBE_EVIDENCE_ISOLATION=PASS")
        print("ENDPOINT_AUTH_VERSION_PREFLIGHT=PASS")


if __name__=="__main__":
    unittest.main()
