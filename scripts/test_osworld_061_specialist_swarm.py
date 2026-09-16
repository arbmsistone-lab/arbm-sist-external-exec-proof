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
        self.assertLessEqual(len(contract),6000)
        self.assertIn('def try_061_calibrated',contract)
        self.assertIn("TASK_ID') != '061'",contract)
        self.assertIn('def _ack_gimp_pending',contract)

    def test_historical_evidence_not_duplicated_in_system_prompt(self):
        contract=swarm.current_contract(); evidence='OLD_FAILURE_UNIQUE_TOKEN'
        system=swarm.role_prompt('state_machine','state machine',contract)
        messages=swarm._text_messages(system,evidence)
        self.assertNotIn(evidence,messages[0]['content'])
        self.assertEqual(messages[1]['content'].count(evidence),1)

if __name__=='__main__': unittest.main()
