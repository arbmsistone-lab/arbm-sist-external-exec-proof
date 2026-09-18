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
 def test_preexisting_inbox_subject_can_verify_opened_message_by_semantic_transition(self):
  m=Milestones()
  title='H2 Rebaseline Directive: Operating Committee Pack'
  before=('menu\tGoogle Chrome\t\t\t\t(99, 0)\t(162, 27)\n'
          'section\t\t'+title+'-The July Operating Committee pack must be reset...\t\t\t(626, 299)\t(976, 20)\n'
          'static\t'+title+'\t'+title+'\t\t\t(626, 300)\t(342, 18)')
  action={'checkpoint':{'name':'COO memo opened','application':'Google Chrome','visible_text':title}}
  m.expect(action,before)
  after=('menu\tGoogle Chrome\t\t\t\t(99, 0)\t(162, 27)\n'
         'heading\t'+title+'\t'+title+'\t\t\t(350, 282)\t(558, 32)\n'
         'paragraph\t\tFollowing the late-Q2 service stability incidents, the July Operating Committee pack needs a disciplined H2 stabilize-and-recover plan.\t\t\t(423, 481)\t(1376, 37)\n'
         'list-item\t\t• Reliability is now a standalone operating function for H2 planning.\t\t\t(463, 705)\t(1336, 19)')
  result=m.observe(after)
  self.assertEqual(result['status'],'VERIFIED')
  self.assertEqual(result['milestone']['verification_basis'],'foreground_content_transition')
  self.assertGreaterEqual(result['milestone']['new_content_count'],2)
  self.assertEqual(m.stalled,0)

 def test_expected_application_transition_is_partial_progress_not_verified(self):
  m=Milestones()
  before=screen('WPS 2019','System Check')
  action={'checkpoint':{'name':'Workbook foreground reached','application':'WPS Spreadsheets',
                        'visible_text':'Reforecast_Model_H2.xlsx workbook with tabs Risk_Register and Roadmap_H2'}}
  m.expect(action,before)
  result=m.observe(screen('WPS Spreadsheets','WPS Spreadsheets'))
  self.assertEqual(result['status'],'PARTIAL_PROGRESS')
  self.assertEqual(result['progress']['application'],'WPS Spreadsheets')
  self.assertEqual(result['progress']['verification_basis'],'expected_application_transition')
  self.assertEqual(m.verified,[])
  self.assertEqual(m.stalled,0)

 def test_wrong_application_transition_remains_unverified(self):
  m=Milestones()
  before=screen('WPS 2019','System Check')
  action={'checkpoint':{'name':'Workbook foreground reached','application':'WPS Spreadsheets',
                        'visible_text':'Reforecast_Model_H2.xlsx'}}
  m.expect(action,before)
  result=m.observe(screen('Google Chrome','Inbox'))
  self.assertEqual(result['status'],'UNVERIFIED')
  self.assertEqual(m.verified,[])
  self.assertEqual(m.stalled,1)

 def test_preexisting_anchor_with_only_trivial_delta_stays_unverified(self):
  m=Milestones(); title='Quarterly Report'
  before=screen('Google Chrome',title)
  m.expect({'checkpoint':{'name':'Report opened','application':'Google Chrome','visible_text':title}},before)
  after=screen('Google Chrome',title)+'\ntext\tPage 2'
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
