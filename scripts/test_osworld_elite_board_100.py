import unittest
from arbm091.elite_board_100 import evaluate, validate_release_receipts

def base_contract():
    expected='H2 Operating Committee Pack\nStabilize-and-Recover Rebaseline'
    return {
        'candidate_sha':'a'*40,
        'before_sha':'b'*64,'after_sha':'c'*64,
        'target':{'source':'task091-pptx-canonical','foreground_sha256':'d'*64,
                  'deck_sha256':'e'*64,'proof_sha256':'f'*64,
                  'cx':869,'cy':391,'w':2,'h':2},
        'shape':{'id':6,'name':'CoverTitle','text':expected,
                 'geometry':{'x':749808,'y':1078992,'w':5852160,'h':1234440}},
        'screen':[0,0,1920,1080],'window':[70,27,1850,1053],
        'viewport':[443,194,1413,795],
        'slide_w':12192000,'slide_h':6858000,
        'generated_point':[869,391],'expected_point':[869,391],
        'expected_shape_id':6,'selected_shape_id':6,
        'expected':expected,'actual':expected,'repair_plan':[],
        'repair_has_pyautogui_write':False,'repair_attempts':0,'repair_shape_id':6,
        'before_old_count':1,'after_old_count':0,'before_new_count':0,'after_new_count':1,
        'save_issued':True,'commit_issued':True,'selection_proven':True,'visual_change_proven':True,
        'advanced_only_after_exact_shape':True,'checkpoint_shape_id':6,
        'ambiguous_shape_blocks':True,'missing_shape_blocks':True,'screen_drift_blocks':True,
        'window_drift_blocks':True,'slide_size_missing_blocks':True,'shape_id_drift_blocks':True,
        'proof_tamper_blocks':True,'cross_shape_edit_blocks':True,'linebreak_loss_blocks':True,
        'second_repair_blocks':True,'corpus_count':8,'proof_tests_required':True,
        'policy_required':True,'replay_required':True,'zero_spend_required':True,
        'immutable_audit_required':True,'merge_blocked':True,'paid_fallback':False,
        'same_sha_required':True,'evidence_reproducible':True,'official_score_gate':1.0,
        'required_consecutive_runs':10,'ten_runs_same_sha':True,'ten_runs_score_1':True,
        'ten_runs_pre_gates_green':True,'ten_runs_artifacts_unique':True,
        'release_default_blocked':True,'promotion_requires_100':True,
        'master_councils_unanimous':True,'no_unresolved_gate':True,
        'zero_spend':'HARD','heavy_local':0,
    }

class EliteBoard100Tests(unittest.TestCase):
    def test_all_100_lanes_and_10_councils_pass(self):
        result=evaluate(base_contract())
        self.assertEqual(result['elite_pass'],100)
        self.assertEqual(result['councils_pass'],10)

    def test_cross_shape_edit_vetoes_promotion(self):
        contract=base_contract(); contract['selected_shape_id']=7
        with self.assertRaisesRegex(RuntimeError,'ELITE_BOARD_BLOCKED'):
            evaluate(contract)

    def test_linebreak_loss_vetoes_promotion(self):
        contract=base_contract()
        contract['actual']=contract['expected'].replace('\n','')
        contract['shape']['text']=contract['actual']
        with self.assertRaisesRegex(RuntimeError,'ELITE_BOARD_BLOCKED'):
            evaluate(contract)

    def test_old_static_coordinate_vetoes_promotion(self):
        contract=base_contract(); contract['generated_point']=[745,335]
        contract['target']['cx']=745; contract['target']['cy']=335
        with self.assertRaisesRegex(RuntimeError,'ELITE_BOARD_BLOCKED'):
            evaluate(contract)

    def test_release_gate_requires_exactly_ten_unique_same_sha_runs(self):
        sha='1'*40
        receipts=[{'run_id':str(1000+i),'artifact_id':str(2000+i),'head_sha':sha,'score':1.0,
                   'proof_tests':'success','policy':'success','replay':'success','focal':'success'}
                  for i in range(10)]
        result=validate_release_receipts(receipts,sha)
        self.assertEqual(result['runs'],10)

    def test_release_gate_rejects_nine_runs(self):
        sha='1'*40
        receipts=[{'run_id':str(1000+i),'artifact_id':str(2000+i),'head_sha':sha,'score':1.0,
                   'proof_tests':'success','policy':'success','replay':'success','focal':'success'}
                  for i in range(9)]
        with self.assertRaisesRegex(RuntimeError,'EXACTLY_TEN_OFFICIAL_RUNS_REQUIRED'):
            validate_release_receipts(receipts,sha)

    def test_release_gate_rejects_one_nonperfect_score(self):
        sha='1'*40
        receipts=[{'run_id':str(1000+i),'artifact_id':str(2000+i),'head_sha':sha,'score':1.0,
                   'proof_tests':'success','policy':'success','replay':'success','focal':'success'}
                  for i in range(10)]
        receipts[7]['score']=0.999
        with self.assertRaisesRegex(RuntimeError,'RUN_8_SCORE_NOT_ONE'):
            validate_release_receipts(receipts,sha)

if __name__=='__main__':
    unittest.main()
