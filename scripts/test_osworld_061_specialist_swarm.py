import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import osworld_061_specialist_swarm as swarm

class SpecialistSwarmTests(unittest.TestCase):
    def verdict(self,role='state_machine'):
        return {'role':role,'verdict':'PASS_FIX','root_cause_class':'AGENT_LOGIC',
                'causal_chain':['historical defect addressed'],'definitive_fix':'none',
                'regression_risks':[],'required_proofs':['official focal'],
                'confidence':0.9,'veto':False}

    def test_verdict_contract_is_strict(self):
        self.assertTrue(swarm.valid_verdict(self.verdict(),'state_machine'))
        self.assertFalse(swarm.valid_verdict(self.verdict('wrong'),'state_machine'))
        bad=self.verdict(); bad['confidence']='high'
        self.assertFalse(swarm.valid_verdict(bad,'state_machine'))

    def test_current_contract_is_compact_and_transactional(self):
        contract=swarm.current_contract()
        self.assertLessEqual(len(contract),9500)
        self.assertIn('def try_061_calibrated',contract)
        self.assertIn("TASK_ID') != '061'",contract)
        self.assertIn('def _ack_gimp_pending',contract)
        self.assertIn('def next_recovery_action',contract)
        self.assertIn('ARBM061_DONE',contract)
        self.assertIn('Export Image as JPEG',contract)
        self.assertIn('calibrated_result=try_061_calibrated',contract)
        self.assertIn('specialist_result=try_gimp_specialist',contract)
        self.assertIn("if state.get('owned') and not state.get('terminal_failed')",contract)
        self.assertIn('Close Sample Colorize only after the remap has finished.',contract)
        self.assertIn('ARBM061_GIMP_EXPORT_PROVENANCE_SUCCESS',contract)

    def test_local_evidence_prioritizes_current_probe(self):
        merged=swarm._local_evidence('OLD_INCIDENT','CURRENT_PROBE')
        self.assertLess(merged.index('CURRENT_PROBE'),merged.index('OLD_INCIDENT'))
        self.assertIn('non-official; no evaluator/score',merged)

    def test_historical_evidence_not_duplicated_in_system_prompt(self):
        contract=swarm.current_contract(); evidence='OLD_FAILURE_UNIQUE_TOKEN'
        system=swarm.role_prompt('state_machine','state machine',contract)
        messages=swarm._text_messages(system,evidence)
        self.assertNotIn(evidence,messages[0]['content'])
        self.assertEqual(messages[1]['content'].count(evidence),1)

    def test_local_text_cache_is_released_before_heavier_vlm(self):
        source=pathlib.Path(swarm.__file__).read_text(encoding='utf-8')
        marker="result=ask(LOCAL_VLM_ROUTE,_vlm_messages(system,evidence,image,probe_evidence),180)"
        pos=source.index(marker)
        window=source[max(0,pos-220):pos]
        self.assertIn('clear_local_text_cache()',window)
        main=source[source.index('def main(root: Path):'):]
        self.assertIn('finally:',main)
        self.assertIn('clear_local_text_cache()',main)

    def test_probe_evidence_is_grounded_and_non_official(self):
        import json,tempfile,os,hashlib
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d); (root/'calibrated').mkdir(); (root/'gimp').mkdir()
            cal_data=b'A'*2048; gimp_data=b'B'*3072
            (root/'calibrated'/'IMG_7318_edited.jpg').write_bytes(cal_data)
            (root/'gimp'/'IMG_7318_edited.jpg').write_bytes(gimp_data)
            (root/'calibrated'/'calibrated-probe-result.json').write_text(json.dumps({
              'status':'CALIBRATED_EXPORT_PROVEN','candidate_sha':'d406','zero_spend_mode':'HARD','heavy_local':0,
              'reference_rmse':4.535,'model':'poly3_residual','output':'IMG_7318_edited.jpg',
              'output_bytes':len(cal_data),'output_sha256':hashlib.sha256(cal_data).hexdigest()}))
            (root/'gimp'/'probe-result.json').write_text(json.dumps({
              'status':'EXPORT_PROVEN','candidate_sha':'d406','zero_spend_mode':'HARD','heavy_local':0,
              'output':'IMG_7318_edited.jpg','output_visible_in_chooser':True,
              'output_bytes':len(gimp_data),'output_sha256':hashlib.sha256(gimp_data).hexdigest()}))
            (root/'gimp'/'output-absent-before-export.txt').write_text('/home/user/Pictures/IMG_7318_edited.jpg')
            stages=('43-sample-colorize-dialog.png','46-subcolors-enabled.png','47-hold-intensity-disabled.png',
              '48-original-intensity-disabled.png','50-sample-colors-loaded.png','60-colorize-applied.png',
              '70-colorize-closed.png','80-export-open-00.png','81-export-name.png','82-export-state-00.png',
              '90-output-chooser.png','91-output-pictures.png')
            for name in stages: (root/'gimp'/name).write_bytes(b'x')
            keys=('DIAGNOSTIC_EXECUTION_PARITY','DIAGNOSTIC_PROBE_RUN_ID','DIAGNOSTIC_PROBE_SHA')
            old={k:os.environ.get(k) for k in keys}
            os.environ.update({'DIAGNOSTIC_EXECUTION_PARITY':'1','DIAGNOSTIC_PROBE_RUN_ID':'35081793502','DIAGNOSTIC_PROBE_SHA':'d406'})
            try: evidence=swarm.load_probe_evidence(root)
            finally:
                for k,v in old.items():
                    if v is None: os.environ.pop(k,None)
                    else: os.environ[k]=v
            self.assertIn('4.535',evidence)
            self.assertIn('diagnostic only, no evaluator/score',evidence)
            self.assertIn('stage_snapshots_present',evidence)


if __name__=='__main__': unittest.main()
