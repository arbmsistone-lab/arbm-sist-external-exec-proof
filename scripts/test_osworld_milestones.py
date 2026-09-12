import unittest
from osworld_milestones import Milestones,verified_facts

def screen(app,text):return 'menu\t'+app+'\t\t\t\t(99, 0)\t(150, 27)\ntext\t'+text

class MilestoneTests(unittest.TestCase):
 def test_actual_archive_open_preserved_not_misread_as_failure(self):
  m=Milestones();before=screen('Google Chrome','Start page')
  m.expect({'checkpoint':{'name':'Source archive opened','application':'Archive Manager','visible_text':'city.zip'}},before)
  result=m.observe(screen('Archive Manager','city.zip'))
  self.assertEqual(result['status'],'VERIFIED');self.assertEqual(m.stalled,0)
  self.assertEqual(m.context()['verified'][0]['visible_text'],'city.zip')
 def test_background_and_preexisting_labels_do_not_prove_success(self):
  for before,after in [(screen('Google Chrome','file.pdf'),screen('Google Chrome','new tab file.pdf')),
                       (screen('Document Viewer','file.pdf'),screen('Document Viewer','file.pdf page2'))]:
   m=Milestones();m.expect({'checkpoint':{'name':'Read source document','application':'Document Viewer','visible_text':'file.pdf'}},before)
   self.assertEqual(m.observe(after)['status'],'UNVERIFIED')
 def test_waits_do_not_consume_budget_but_unverified_changes_do(self):
  m=Milestones()
  for i in range(13):
   m.expect({},screen('Files',str(i)));m.observe(screen('Files',str(i+1)))
  self.assertEqual(m.stalled,13)
  for _ in range(40):m.observe(screen('Files','unchanged'))
  self.assertEqual(m.stalled,13)
 def test_duplicate_milestone_cannot_reset_loop_budget(self):
  m=Milestones();a={'checkpoint':{'name':'Archive source open','application':'Archive Manager','visible_text':'city.zip'}}
  for _ in range(3):m.expect(a,screen('Files','folder'));m.observe(screen('Archive Manager','city.zip'))
  self.assertEqual(len(m.verified),1);self.assertEqual(m.stalled,2)
 def test_only_exact_current_source_quotes_are_retained(self):
  obs=screen('LibreOffice Calc','FYP12345 Leslie Adams 14:30 Room 201')
  facts=verified_facts({'observed_facts':[{'quote':'FYP12345 Leslie Adams 14:30 Room 201'},{'quote':'All appointments already saved'}]},obs)
  self.assertEqual(len(facts),1);self.assertIn('14:30',facts[0]['quote'])
 def test_hidden_file_metadata_is_not_verified_source(self):
  obs=screen('Archive Manager','Archive contents')+'\nlabel\tsecret.pdf\tsecret.pdf\t\t\t(1800, 800)\t(100, 20)'
  self.assertEqual(verified_facts({'observed_facts':[{'quote':'secret.pdf'}]},obs),[])
if __name__=='__main__':unittest.main()
