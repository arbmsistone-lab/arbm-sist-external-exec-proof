import pathlib, sys, tempfile, unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).parent))
import osworld_incident_consensus as c

def verdict(root='PROVIDER_CAPACITY',dissent=False):
 return {'verdict':{'root_cause_class':root,'causal_chain':'evidence','recommended_fix':'fix','regression_risk':'low','confidence':0.99,'critical_dissent':dissent},'attempts':[],'raw':''}

class ConsensusTests(unittest.TestCase):
 def evidence(self):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
  p=pathlib.Path(t.name);(p/'osworld.log').write_text('provider capacity failure evidence')
  return p

 def test_five_reviewers_accept_three_vote_consensus(self):
  root=self.evidence();local=[verdict(),verdict()];remote=[verdict(),verdict('AGENT_LOGIC'),verdict('AGENT_LOGIC')]
  with patch.object(c,'local_text_review',side_effect=local),patch.object(c,'ask',side_effect=remote),patch.object(c.Path,'write_text',return_value=None):
   c.main(root)

 def test_critical_dissent_blocks_consensus(self):
  root=self.evidence();local=[verdict(),verdict(dissent=True)];remote=[verdict(),verdict(),verdict()]
  with patch.object(c,'local_text_review',side_effect=local),patch.object(c,'ask',side_effect=remote),patch.object(c.Path,'write_text',return_value=None):
   with self.assertRaisesRegex(RuntimeError,'MULTI_AI_CONSENSUS_NOT_REACHED'):c.main(root)

 def test_codex_required_mode_fails_closed_when_review_missing(self):
  root=self.evidence();missing=root/'codex.json'
  local=[verdict(),verdict()];remote=[verdict(),verdict(),verdict()]
  with patch.object(c,'local_text_review',side_effect=local),patch.object(c,'ask',side_effect=remote):
   with self.assertRaisesRegex(RuntimeError,'CODEX_REVIEW_REQUIRED_BUT_MISSING'):
    c.main(root,str(missing))

if __name__=='__main__':unittest.main()
