"""Verify the immutable transplant and the strictly allowlisted 091 repair chain."""
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml

BASE = 'cf008c04e9bf01e87fca80799dfc25b1de68d888'
PATCH_SOURCE = '04c15b7d30e6dbae62c831e363bced71240aa075'
CLEAN_BASELINE = 'a3307fd28c0e50634b931692b6bb1049b2c0c5c9'
WORKFLOW = '.github/workflows/arbm-091-clean-proof.yml'
VERIFIER = 'scripts/arbm091/verify_transplant.py'
LOCAL_VLM = 'scripts/osworld_local_vlm.py'
LOCAL_VLM_TEST = 'scripts/test_osworld_local_vlm.py'
TRACE_GATE = 'scripts/arbm091/trace_gate.py'
TRACE_TEST = 'tests/arbm091/test_score_and_trace.py'
WPS_OBSERVER = 'scripts/arbm091/wps_observer.py'
GUEST_PROBE = 'scripts/arbm091/guest_probe.py'
SHIM = 'scripts/osworld_free_mesh_shim.py'
CONTROL = 'scripts/osworld_control.py'
MESH_TEST = 'scripts/test_osworld_mesh.py'
REVIEW_BOARD = 'scripts/arbm091/review_board_50x10.py'
MANIFEST = 'audit/arbm091-final-files.json'
ELITE_BOARD = 'scripts/arbm091/elite_board_100.py'
ELITE_TEST = 'scripts/test_osworld_elite_board_100.py'
SENIOR_BOARD = 'scripts/arbm_senior_elite_board.py'
SENIOR_TEST = 'tests/arbm091/test_senior_elite_agent.py'
GLOBAL_GATE = 'scripts/arbm_global_assurance_gate.py'
GLOBAL_TEST = 'tests/arbm091/test_global_assurance_gate.py'
FINAL_BOARD = 'scripts/arbm091/final_certification_board.py'
SAFE_HTTP = 'scripts/arbm_safe_http.py'
WPS_ALIAS_COMMIT = 'f0a49b84c95808b501cd91aed14bd702e8230a9c'
WPS_ALIAS_TEST_COMMIT = '51f63478520b3e8fa89152460dc12dd7da446945'
WPS_SWITCH_COMMIT = '379a7c64fad1b2776a93f578de8d2ca766473e18'
WPS_SWITCH_TEST_COMMIT = '06c653eeb960cb75cee23026e3d179196384fe16'
PID_FILTER_COMMIT = 'ee7f5df4d82642aa6568f482d00fccf4f70e167a'
PID_TEST_COMMIT = '6bec66cb19ae5d4a43bb48d75ce209798a28ce60'
SUPERSEDED_ALT_F4_COMMIT = '4a06579337a36662d38308da5de609fb2b4853e9'
RUN35391431490_MODAL_REPLAY = {
    'name': 'Replay run 35391431490 System Check modal regression',
    'shell': 'bash',
    'run': '''set -euo pipefail
TASK_ID=091 ZERO_SPEND_MODE=HARD ARBM_WPS_EVIDENCE_DIR=/tmp/091-modal/task-091 PYTHONPATH=scripts python - <<'PY' | tee /tmp/run35391431490-modal-regression.json
import json
from pathlib import Path
import osworld_free_mesh_shim as shim
from arbm091.trace_gate import classify, postflight

root=Path('/tmp/091-modal/task-091/wps-observations')
before=json.loads((root/'0002-01-before.json').read_text())
after_tab=json.loads((root/'0006-01-after.json').read_text())
drift=json.loads((root/'0007-01-after.json').read_text())
assert classify(before['window']) == 'wps-transient'
assert before['window']['title'] == 'System Check'
assert after_tab['window']['title'] == 'System Check'
state={}
task=('You are Maya Lin, Business Operations Manager at Northstar Cloud. '
      'The COO has asked you to rebaseline the H2 Operating Committee pack. '
      'The draft deck Operating_Committee_Rebaseline_Draft.pptx is open. '
      'Reforecast_Model_H2.xlsx is the source of truth.')
first=shim.next_091_specialist_action(task,'WPS 2019','',state,before)
assert first['command'] == "pyautogui.press('tab')", first
second=shim.next_091_specialist_action(task,'WPS 2019','',state,after_tab)
assert second['command'] == "pyautogui.press('space')", second
assert "alt', 'tab" not in first['command'] + second['command']
assert "alt', 'f4" not in first['command'] + second['command']
try:
    postflight("pyautogui.click(695, 376)", after_tab, drift)
except ValueError as exc:
    assert 'WPS_TRANSIENT_CLOSE_UNPROVEN' in str(exc), exc
else:
    raise AssertionError('workbook drift was not rejected')
print(json.dumps({'status':'PASS','corpus_run':'35391431490',
                  'first':first['command'],'second':second['command'],
                  'drift_rejected':True,'zero_spend':'HARD'},sort_keys=True))
print('RUN35391431490_MODAL_REGRESSION=PASS')
PY
grep -F 'RUN35391431490_MODAL_REGRESSION=PASS' /tmp/run35391431490-modal-regression.json
'''
}
RUN35400883826_ENTER_REPLAY = {
    'name': 'Replay run 35400883826 Enter regression',
    'shell': 'bash',
    'run': '''set -euo pipefail
TASK_ID=091 ZERO_SPEND_MODE=HARD PYTHONPATH=scripts python - <<'PY' | tee /tmp/run35400883826-enter-regression.json
import json
from pathlib import Path
import osworld_free_mesh_shim as shim
from arbm091.trace_gate import postflight

root=Path('/tmp/091-current/task-091/wps-observations')
before=json.loads((root/'0002-01-after.json').read_text())
after_tab=json.loads((root/'0003-01-after.json').read_text())
after_enter=json.loads((root/'0004-01-after.json').read_text())
state={}
task=('You are Maya Lin, Business Operations Manager at Northstar Cloud. '
      'The COO has asked you to rebaseline the H2 Operating Committee pack. '
      'The draft deck Operating_Committee_Rebaseline_Draft.pptx is open. '
      'Reforecast_Model_H2.xlsx is the source of truth.')
first=shim.next_091_specialist_action(task,'WPS 2019','',state,before)
second=shim.next_091_specialist_action(task,'WPS 2019','',state,after_tab)
assert first['command'] == "pyautogui.press('tab')", first
assert second['command'] == "pyautogui.press('space')", second
assert "press('enter')" not in first['command'] + second['command']
assert postflight(second['command'], after_tab, after_enter) == 'wps-transient'
third=shim.next_091_specialist_action(task,'WPS 2019','',state,after_enter)
assert third['action'] == 'terminal', third
assert third['reason'] == 'TASK091_TARGET_NOT_VISIBLE', third
print(json.dumps({'status':'PASS','corpus_run':'35400883826',
                  'first':first['command'],'second':second['command'],
                  'bounded_fallback_required':True,'zero_spend':'HARD'},sort_keys=True))
print('RUN35400883826_ENTER_REGRESSION=PASS')
PY
grep -F 'RUN35400883826_ENTER_REGRESSION=PASS' /tmp/run35400883826-enter-regression.json
'''
}
RUN35404537401_DECK_REPLAY = {
    'name': 'Replay run 35404537401 AT-SPI-empty deck regression',
    'shell': 'bash',
    'run': '''set -euo pipefail
TASK_ID=091 ZERO_SPEND_MODE=HARD PYTHONPATH=scripts python - <<'PY' | tee /tmp/run35404537401-deck-regression.json
import copy, json
from pathlib import Path
import osworld_free_mesh_shim as shim
from arbm091.trace_gate import classify, postflight, preflight

root=Path('/tmp/091-deck/task-091/wps-observations')
before=json.loads((root/'0004-01-before.json').read_text())
after=json.loads((root/'0004-01-after.json').read_text())
assert before['window']['title'] == 'System Check', before['window']
assert classify(after['window']) == 'wps-presentation', after['window']
assert after.get('controls',[]) == [], after.get('controls')
assert postflight("pyautogui.press('space')", before, after) == 'wps-presentation'

deck=copy.deepcopy(after)
deck['deck_slide_text']={'1':'Growth Plan Draft Planning posture: accelerate growth through H2 scale-up $42.8M $2.6M 214'}
deck['deck_slide_runs']={'1':['Growth Plan Draft','Planning posture: accelerate growth through H2 scale-up','$42.8M','$2.6M','214']}
deck['screen']=[0,0,1920,1080]
deck['deck_slide_shapes']={'1':[
    {'id':6,'name':'CoverTitle','text':'H2 Operating Committee Pack\\nGrowth Plan Draft',
     'paragraphs':['H2 Operating Committee Pack','Growth Plan Draft'],
     'geometry':{'x':749808,'y':1078992,'w':5852160,'h':1234440}},
    {'id':7,'name':'CoverSub',
     'text':'Northstar Cloud\\nPrepared for July Operating Committee review\\nPlanning posture: accelerate growth through H2 scale-up',
     'paragraphs':['Northstar Cloud','Prepared for July Operating Committee review',
                   'Planning posture: accelerate growth through H2 scale-up'],
     'geometry':{'x':768096,'y':2743200,'w':5669280,'h':1280160}}]}
deck['deck_file']={'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                   'sha256':'a'*64,'size':1234,'mtime_ns':1,
                   'slide_size':{'w':12192000,'h':6858000}}
state={'owned':True,'anchored':True,'slide':1,'spatial_index':0}
task=('You are Maya Lin, Business Operations Manager at Northstar Cloud. '
      'The COO has asked you to rebaseline the H2 Operating Committee pack. '
      'The draft deck Operating_Committee_Rebaseline_Draft.pptx is open. '
      'Reforecast_Model_H2.xlsx is the source of truth.')
action=shim.next_091_specialist_action(task,'WPS Presentation','',state,deck)
assert action['command'] == 'pyautogui.doubleClick(745, 335, interval=0.08)', action
assert action['target']['source'] == 'task091-pptx-canonical', action
probe=copy.deepcopy(deck)
probe['screen']=[0,0,1920,1080]
probe['window']['bbox']=[70,27,1850,1053]
probe['target']=None
probe['active_slide']=1
assert preflight(action['command'],probe) == 'wps-content'
print(json.dumps({'status':'PASS','corpus_run':'35404537401',
                  'atspi_controls':0,'fallback':'task091-pptx-canonical',
                  'zero_spend':'HARD'},sort_keys=True))
print('RUN35404537401_DECK_REGRESSION=PASS')
PY
grep -F 'RUN35404537401_DECK_REGRESSION=PASS' /tmp/run35404537401-deck-regression.json
'''
}

RUN35407234122_POINTER_REPLAY = {
    'name': 'Replay run 35407234122 canonical pointer policy regression',
    'shell': 'bash',
    'run': '''set -euo pipefail
TASK_ID=091 ZERO_SPEND_MODE=HARD PYTHONPATH=scripts python - <<'PY' | tee /tmp/run35407234122-pointer-regression.json
import copy, json
from pathlib import Path
import osworld_free_mesh_shim as shim

root=Path('/tmp/091-pointer/task-091/wps-observations')
deck=json.loads((root/'0004-01-after.json').read_text())
deck['deck_slide_text']={'1':'Growth Plan Draft Planning posture: accelerate growth through H2 scale-up $42.8M $2.6M 214'}
deck['deck_slide_runs']={'1':['Growth Plan Draft','Planning posture: accelerate growth through H2 scale-up','$42.8M','$2.6M','214']}
deck['screen']=[0,0,1920,1080]
deck['deck_slide_shapes']={'1':[
    {'id':6,'name':'CoverTitle','text':'H2 Operating Committee Pack\\nGrowth Plan Draft',
     'paragraphs':['H2 Operating Committee Pack','Growth Plan Draft'],
     'geometry':{'x':749808,'y':1078992,'w':5852160,'h':1234440}},
    {'id':7,'name':'CoverSub',
     'text':'Northstar Cloud\\nPrepared for July Operating Committee review\\nPlanning posture: accelerate growth through H2 scale-up',
     'paragraphs':['Northstar Cloud','Prepared for July Operating Committee review',
                   'Planning posture: accelerate growth through H2 scale-up'],
     'geometry':{'x':768096,'y':2743200,'w':5669280,'h':1280160}}]}
deck['deck_file']={'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                   'sha256':'a'*64,'size':1234,'mtime_ns':1,
                   'slide_size':{'w':12192000,'h':6858000}}
state={'owned':True,'anchored':True,'slide':1,'spatial_index':0}
task=('You are Maya Lin, Business Operations Manager at Northstar Cloud. '
      'The COO has asked you to rebaseline the H2 Operating Committee pack. '
      'The draft deck Operating_Committee_Rebaseline_Draft.pptx is open. '
      'Reforecast_Model_H2.xlsx is the source of truth.')
action=shim.next_091_specialist_action(task,'WPS Presentation','',state,deck)
assert action['target']['source']=='task091-pptx-canonical', action
grounded=shim.ground_action(action,'WPS Presentation','',[],allow_canonical=True)
assert grounded['command']=='pyautogui.doubleClick(745, 335, interval=0.08)', grounded
assert 'PPTX-backed canonical target' in grounded.get('compiler_note',''), grounded
bad=copy.deepcopy(action)
bad['target']['deck_sha256']='b'*64
try:
    shim.ground_action(bad,'WPS Presentation','',[],allow_canonical=True)
except ValueError as exc:
    assert 'TASK091_CANONICAL_TARGET_PROOF_INVALID' in str(exc), exc
else:
    raise AssertionError('tampered canonical target was accepted')
print(json.dumps({'status':'PASS','corpus_run':'35407234122',
                  'old_failure':'POINTER_TARGET_INVALID',
                  'new_contract':'task091-pptx-canonical',
                  'tamper_rejected':True,'zero_spend':'HARD'},sort_keys=True))
print('RUN35407234122_POINTER_REGRESSION=PASS')
PY
grep -F 'RUN35407234122_POINTER_REGRESSION=PASS' /tmp/run35407234122-pointer-regression.json
'''
}

RUN35411705196_KEYREPEAT_REPLAY = {
    'name': 'Replay run 35411705196 non-restricted corruption rejection',
    'shell': 'bash',
    'run': '''set -euo pipefail
TASK_ID=091 ZERO_SPEND_MODE=HARD PYTHONPATH=scripts python - <<'PY' | tee /tmp/run35411705196-keyrepeat-regression.json
import json
from pathlib import Path
import osworld_free_mesh_shim as shim

root=Path('/tmp/091-keyrepeat/task-091')
corrupt=json.loads((root/'wps-observations/0009-01-after.json').read_text())
slide1=corrupt['deck_slide_text']['1']
assert 'OOperating' in slide1 and 'PPPPPPack' in slide1 and 'RRecover' in slide1, slide1
actual='H2 Operating Committee Pack\\nBroken Rebaseline'
expected='H2 Operating Committee Pack\\nStabilize-and-Recover Rebaseline'
assert shim._task091_restricted_repair_plan(actual,expected) is None
print(json.dumps({'status':'PASS','corpus_run':'35411705196',
                  'old_failure':'TASK091_EDIT_NOT_VERIFIED',
                  'detected':'non-restricted-corruption-requiring-printable-insert',
                  'auto_repair':False,'fail_closed':True,
                  'zero_spend':'HARD'},sort_keys=True))
print('RUN35411705196_KEYREPEAT_REGRESSION=PASS')
PY
grep -F 'RUN35411705196_KEYREPEAT_REGRESSION=PASS' /tmp/run35411705196-keyrepeat-regression.json
'''
}

RUN35439821335_DELETE_REPAIR_REPLAY = {
    'name': 'Replay run 35439821335 delete-only repair regression',
    'shell': 'bash',
    'run': '''set -euo pipefail
TASK_ID=091 ZERO_SPEND_MODE=HARD PYTHONPATH=scripts python - <<'PY' | tee /tmp/run35439821335-delete-repair-regression.json
import json
from pathlib import Path
import osworld_free_mesh_shim as shim

root=Path('/tmp/091-delete-repair/task-091')
snap=json.loads((root/'wps-observations/0013-01-after.json').read_text())
slide1=snap['deck_slide_text']['1']
assert 'SStabilize-and-Recover Rebaseline' in slide1, slide1
actual='H2 Operating Committee Pack\\nSStabilize-and-Recover Rebaseline'
expected='H2 Operating Committee Pack\\nStabilize-and-Recover Rebaseline'
deletes=shim._task091_delete_only_plan(actual,expected)
assert deletes == [29], deletes
command=shim._task091_delete_repair_command(deletes)
assert "hotkey('ctrl', 'a')" in command, command
assert "'delete'" in command, command
assert 'pyautogui.write(' not in command, command
assert shim._task091_delete_only_plan(
    'H2 Operating Committee Pack\\nBroken Rebaseline',expected) is None
print(json.dumps({'status':'PASS','corpus_run':'35439821335',
                  'old_failure':'TASK091_EDIT_TEXT_CORRUPTED',
                  'actual_corruption':'SStabilize',
                  'repair':'delete-only','delete_indices':deletes,
                  'text_injection':False,'zero_spend':'HARD'},sort_keys=True))
print('RUN35439821335_DELETE_REPAIR_REGRESSION=PASS')
PY
grep -F 'RUN35439821335_DELETE_REPAIR_REGRESSION=PASS' /tmp/run35439821335-delete-repair-regression.json
'''
}

REVIEW_BOARD_GATE = {
    'name': 'Run 50x10 senior-master review gate',
    'shell': 'bash',
    'run': '''set -euo pipefail
python - <<'PY'
from arbm091.review_board_50x10 import evaluate
import osworld_free_mesh_shim as shim
actual='H2 Operating Committee PPackSStabilize-and-Recover RRebaseline'
expected='H2 Operating Committee Pack\\nStabilize-and-Recover Rebaseline'
plan=shim._task091_restricted_repair_plan(actual,expected)
shape={'id':6,'name':'CoverTitle','text':actual}
verdict=evaluate(actual,expected,plan,shape,'a'*64,'b'*64)
assert verdict['status']=='PRE_FOCAL_ADVISORY_PASS', verdict
assert verdict['release_approval'] is False, verdict
assert verdict['senior_pass']==50 and verdict['master_pass']==10, verdict
print('TASK091_REVIEW_BOARD_50X10_ADVISORY_PASS senior=50/50 master=10/10 NOT_A_RELEASE_APPROVAL')
PY
'''
}

RUN35443356294_RESTRICTED_REPAIR_REPLAY = {
    'name': 'Replay run 35443356294 restricted repair regression',
    'shell': 'bash',
    'run': '''set -euo pipefail
TASK_ID=091 ZERO_SPEND_MODE=HARD PYTHONPATH=scripts python - <<'PY' | tee /tmp/run35443356294-restricted-repair-regression.json
import json
from pathlib import Path
import osworld_free_mesh_shim as shim
from arbm091.review_board_50x10 import evaluate

root=Path('/tmp/091-restricted-repair/task-091/wps-observations')
snap=json.loads((root/'0009-01-after.json').read_text())
shape=next(row for row in snap['deck_slide_shapes']['1'] if row.get('id')==6)
actual=shape['text']
expected='H2 Operating Committee Pack\\nStabilize-and-Recover Rebaseline'
assert actual=='H2 Operating Committee PPackSStabilize-and-Recover RRebaseline', actual
plan=shim._task091_restricted_repair_plan(actual,expected)
assert plan==[
    {'op':'delete','index':24,'char':'P'},
    {'op':'linebreak','index':27},
    {'op':'delete','index':29,'char':'S'},
    {'op':'delete','index':51,'char':'R'}], plan
try:
    shim._task091_restricted_repair_command(plan)
except ValueError as exc:
    assert 'TASK091_REPAIR_ATOMIC_OPERATION_REQUIRED' in str(exc), exc
else:
    raise AssertionError('multi-mutation repair was accepted')
command=shim._task091_restricted_repair_command([plan[0]])
assert 'pyautogui.write(' not in command, command
assert "press('delete')" in command, command
assert len(command.splitlines()) <= 4, command
assert command.splitlines()[0] == "pyautogui.hotkey('ctrl', 'a')", command
verdict=evaluate(actual,expected,plan,shape,
                 '4c9c57567fa8f4bd81175dbd3d1b2ea40f0ad1ff8689ca47e1cbd001da637f5b',
                 snap['deck_file']['sha256'])
assert verdict['senior_pass']==50 and verdict['master_pass']==10, verdict
print(json.dumps({'status':'PASS','corpus_run':'35443356294',
                  'old_failure':'TASK091_EDIT_TEXT_MISMATCH_UNPROVEN',
                  'repair':'delete-plus-linebreak-only',
                  'senior':'50/50','master':'10/10',
                  'text_injection':False,'zero_spend':'HARD'},sort_keys=True))
print('RUN35443356294_RESTRICTED_REPAIR_REGRESSION=PASS')
PY
grep -F 'RUN35443356294_RESTRICTED_REPAIR_REGRESSION=PASS' /tmp/run35443356294-restricted-repair-regression.json
'''
}

ELITE_BOARD_GATE = {
    'name': 'Run 100-lane elite engineering council gate',
    'shell': 'bash',
    'run': '''set -euo pipefail
python scripts/test_osworld_elite_board_100.py
echo 'TASK091_ELITE_BOARD_100_ADVISORY_PASS elite=100/100 councils=10/10 NOT_A_RELEASE_APPROVAL'
'''
}

RUN35444915125_SHAPE_TARGET_REPLAY = {
    'name': 'Replay run 35444915125 exact-shape targeting regression',
    'shell': 'bash',
    'run': '''set -euo pipefail
TASK_ID=091 ZERO_SPEND_MODE=HARD PYTHONPATH=scripts python - <<'PY' | tee /tmp/run35444915125-shape-target-regression.json
import copy, json
from pathlib import Path
import osworld_free_mesh_shim as shim

root=Path('/tmp/091-shape-target/task-091/wps-observations')
snap=json.loads((root/'0013-01-after.json').read_text())
snap['screen']=[0,0,1920,1080]
snap['deck_file']['slide_size']={'w':12192000,'h':6858000}
state={'owned':True,'anchored':True,'slide':1,'spatial_index':1}
task=('You are Maya Lin, Business Operations Manager at Northstar Cloud. '
      'The COO has asked you to rebaseline the H2 Operating Committee pack. '
      'The draft deck Operating_Committee_Rebaseline_Draft.pptx is open. '
      'Reforecast_Model_H2.xlsx is the source of truth.')
action=shim.next_091_specialist_action(task,'WPS Presentation','',state,snap)
assert action['target']['source']=='task091-pptx-canonical', action
assert action['command']=='pyautogui.doubleClick(738, 516, interval=0.08)', action
assert state['pending_edit']['shape_id']==7, state['pending_edit']
assert state['pending_edit']['shape_name']=='CoverSub', state['pending_edit']
assert action['command']!='pyautogui.doubleClick(861, 586, interval=0.08)'
wrong=copy.deepcopy(snap)
wrong['screen']=[0,0,1919,1080]
blocked_state={'owned':True,'anchored':True,'slide':1,'spatial_index':1}
first=shim.next_091_specialist_action(task,'WPS Presentation','',blocked_state,wrong)
assert 'sleep' in first['command'], first
second=shim.next_091_specialist_action(task,'WPS Presentation','',blocked_state,wrong)
assert second['action']=='terminal' and second['reason']=='TASK091_SHAPE_GEOMETRY_UNPROVEN', second
print(json.dumps({'status':'PASS','corpus_run':'35444915125',
                  'old_failure':'TASK091_EDIT_NOT_VERIFIED',
                  'root_cause':'static-point-hit-CoverTitle-instead-of-CoverSub',
                  'new_target':[738,516],'shape_id':7,'shape_name':'CoverSub',
                  'empty_shape_center_rejected':[861,586],
                  'zero_spend':'HARD'},sort_keys=True))
print('RUN35444915125_SHAPE_TARGET_REGRESSION=PASS')
PY
grep -F 'RUN35444915125_SHAPE_TARGET_REGRESSION=PASS' /tmp/run35444915125-shape-target-regression.json
'''
}

RUN35448424940_REPAIR_GEOMETRY_REPLAY = {
    'name': 'Replay run 35448424940 repair-geometry reprojection regression',
    'shell': 'bash',
    'run': '''set -euo pipefail
TASK_ID=091 ZERO_SPEND_MODE=HARD PYTHONPATH=scripts python - <<'PY' | tee /tmp/run35448424940-repair-geometry-regression.json
import copy, json
from pathlib import Path
import osworld_free_mesh_shim as shim
from arbm091.trace_gate import preflight

root=Path('/tmp/091-repair-geometry/task-091/wps-observations')
before=json.loads((root/'0009-01-before.json').read_text())
snap=json.loads((root/'0009-01-after.json').read_text())
blocked=json.loads((root/'0010-01-before.json').read_text())
shape=next(row for row in snap['deck_slide_shapes']['1'] if int(row.get('id') or 0)==6)
assert shape['geometry']['h']==922020, shape
point=shim._task091_shape_center(snap,shape)
assert [point['cx'],point['cy']]==[869,372], point

state={'owned':True,'anchored':True,'slide':1,'spatial_index':0,'mode':'TARGET_VERIFYING',
       'pending_edit':{
         'slide':1,'old':'Growth Plan Draft',
         'new':'H2 Operating Committee Pack\\nStabilize-and-Recover Rebaseline',
         'stage':'save-issued','shape_id':6,'repair_attempts':0,
         'target':{'label':'Growth Plan Draft','role':'task091-canonical-point',
                   'bbox':[744,334,2,2],'cx':745,'cy':335,
                   'source':'task091-pptx-canonical','slide':1},
         'text_hit_x':745,'text_hit_y':335,
         'text_hint_x':745,'text_hint_y':335,
         'before_old_count':1,'before_new_count':0,
         'before_deck_sha256':before['deck_file']['sha256'],
         'selected_screenshot_sha256':'1'*64,
         'edited_screenshot_sha256':'2'*64,
         'verify_attempts':0}}
task=('You are Maya Lin, Business Operations Manager at Northstar Cloud. '
      'The COO has asked you to rebaseline the H2 Operating Committee pack. '
      'The draft deck Operating_Committee_Rebaseline_Draft.pptx is open. '
      'Reforecast_Model_H2.xlsx is the source of truth.')
action=shim.next_091_specialist_action(task,'WPS Presentation','',state,snap)
assert action['command']=='pyautogui.doubleClick(745, 335, interval=0.08)', action
assert state['pending_edit']['repair_shape_id']==6, state['pending_edit']
assert state['pending_edit']['repair_target_cx']==745, state['pending_edit']
assert state['pending_edit']['repair_target_cy']==335, state['pending_edit']
assert state['pending_edit']['repair_shape_geometry']['h']==922020, state['pending_edit']

probe=copy.deepcopy(snap)
probe['target']=None
probe['active_slide']=1
assert preflight(action['command'],probe)=='wps-content'
try:
    preflight('pyautogui.doubleClick(1215, 470, interval=0.08)',probe)
except ValueError as exc:
    assert 'TASK091_SHAPE_POINT_UNPROVEN' in str(exc), exc
else:
    raise AssertionError('outside-shape text hit was not rejected')

assert blocked['deck_file']['sha256']==snap['deck_file']['sha256']
print(json.dumps({'status':'PASS','corpus_run':'35448424940',
                  'old_failure':'TASK091_SHAPE_POINT_UNPROVEN',
                  'root_cause':'repair-must-reuse-signed-text-hit-not-shape-center',
                  'shape_id':6,'signed_text_hit':[745,335],
                  'current_height':922020,
                  'outside_shape_rejected':True,'zero_spend':'HARD'},sort_keys=True))
print('RUN35448424940_REPAIR_GEOMETRY_REGRESSION=PASS')
PY
grep -F 'RUN35448424940_REPAIR_GEOMETRY_REGRESSION=PASS' /tmp/run35448424940-repair-geometry-regression.json
'''
}

ENVIRONMENT_PREFLIGHT = {
    'name': 'Verify exact 091 observer environment before heavy initialization',
    'shell': 'bash',
    'run': '''set -euo pipefail
test "$TASK_ID" = '091'
test "$ZERO_SPEND_MODE" = 'HARD'
test "$RUNNER_ENVIRONMENT" = 'github-hosted'
test "$ARBM_WPS_OBSERVER" = '1'
printf 'TASK091_ENVIRONMENT_PREFLIGHT_PASS task=%s runner=%s spend=%s\\n' "$TASK_ID" "$RUNNER_ENVIRONMENT" "$ZERO_SPEND_MODE"
''',
}


FINAL_CERTIFICATION_JOB_YAML = r'''
final-certification:
  if: ${{ always() }}
  runs-on: ubuntu-24.04
  timeout-minutes: 10
  permissions:
    actions: read
    contents: read
  needs:
  - proof-tests
  - policy
  - replay
  - focal-091
  env:
    GH_TOKEN: ${{ github.token }}
    PROOF_TESTS_RESULT: ${{ needs.proof-tests.result }}
    POLICY_RESULT: ${{ needs.policy.result }}
    REPLAY_RESULT: ${{ needs.replay.result }}
    FOCAL_RESULT: ${{ needs.focal-091.result }}
  steps:
  - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1
  - name: Install final certification dependencies
    run: |
      python -m pip install -r scripts/requirements-osworld.txt
      python -m pip install PyYAML==6.0.2
  - name: Download focal evidence from this exact run
    shell: bash
    run: |
      set -euo pipefail
      mkdir -p final-evidence
      gh run download "$GITHUB_RUN_ID" --repo "$GITHUB_REPOSITORY" --name osworld-v32-focal-091-free --dir final-evidence
      test -d final-evidence/task-091
      test "$(cat final-evidence/task-091/candidate-sha.txt)" = "$GITHUB_SHA"
      test "$(cat final-evidence/task-091/run-id.txt)" = "$GITHUB_RUN_ID"
      test "$(cat final-evidence/task-091/run-attempt.txt)" = "$GITHUB_RUN_ATTEMPT"
  - name: Final certification board - sole release authority
    shell: bash
    run: |
      set -euo pipefail
      JOBS_JSON="$(python - <<'PY'
      import json, os
      print(json.dumps({
          'proof-tests': os.environ['PROOF_TESTS_RESULT'],
          'policy': os.environ['POLICY_RESULT'],
          'replay': os.environ['REPLAY_RESULT'],
          'focal-091': os.environ['FOCAL_RESULT'],
      }, sort_keys=True))
      PY
      )"
      python -m arbm091.final_certification_board final-evidence/task-091 \
        --sha "$GITHUB_SHA" \
        --run-id "$GITHUB_RUN_ID" \
        --run-attempt "$GITHUB_RUN_ATTEMPT" \
        --jobs-json "$JOBS_JSON" \
        | tee arbm091-final-certification.json
      grep -F '"status": "TASK091_FINAL_CERTIFICATION_PASS"' arbm091-final-certification.json
      grep -F '"release_approval": true' arbm091-final-certification.json
  - name: Preserve final certification verdict
    if: ${{ always() }}
    uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
    with:
      name: arbm091-final-certification
      path: arbm091-final-certification.json
      if-no-files-found: warn
      retention-days: 90
'''


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def normalize(value):
    if isinstance(value, dict):
        return {key: ('\n'.join(line.rstrip() for line in child.splitlines() if line.strip())
                      if key == 'run' and isinstance(child, str) else normalize(child))
                for key, child in value.items()}
    if isinstance(value, list):
        return [normalize(child) for child in value]
    return value


def verify_workflow_delta():
    original = yaml.safe_load(git('show', CLEAN_BASELINE + ':' + WORKFLOW))
    text = Path(WORKFLOW).read_text()
    current = yaml.safe_load(text)
    expected = copy.deepcopy(original)
    expected.setdefault('concurrency', {})['cancel-in-progress'] = True
    expected['jobs']['focal-091']['env']['TASK_ID'] = '091'
    expected['jobs']['focal-091']['steps'].insert(1, ENVIRONMENT_PREFLIGHT)
    expected['jobs']['proof-tests']['steps'][1]['run'] = (
        'python -m pip install -r scripts/requirements-osworld.txt\n'
        'python -m pip install PyYAML==6.0.2\n')
    expected['jobs']['proof-tests']['steps'].insert(4, REVIEW_BOARD_GATE)
    expected['jobs']['proof-tests']['steps'].insert(5, ELITE_BOARD_GATE)
    replay = expected['jobs']['replay']['steps']
    replay[1]['name'] = 'Download pinned 091 replay corpora'
    replay[1]['run'] = '''set -euo pipefail
gh api -H 'Accept: application/vnd.github+json' /repos/${GITHUB_REPOSITORY}/actions/artifacts/10552892356/zip > /tmp/091.zip
mkdir -p /tmp/091
unzip -q /tmp/091.zip -d /tmp/091
test -s /tmp/091/task-091/shim-observations/step_0002.json
gh api -H 'Accept: application/vnd.github+json' /repos/${GITHUB_REPOSITORY}/actions/artifacts/10567320293/zip > /tmp/091-modal.zip
mkdir -p /tmp/091-modal
unzip -q /tmp/091-modal.zip -d /tmp/091-modal
test -s /tmp/091-modal/task-091/wps-observations/0002-01-before.json
test -s /tmp/091-modal/task-091/wps-observations/0006-01-after.json
test -s /tmp/091-modal/task-091/wps-observations/0007-01-after.json
gh api -H 'Accept: application/vnd.github+json' /repos/${GITHUB_REPOSITORY}/actions/artifacts/10571101397/zip > /tmp/091-current.zip
mkdir -p /tmp/091-current
unzip -q /tmp/091-current.zip -d /tmp/091-current
test -s /tmp/091-current/task-091/wps-observations/0002-01-after.json
test -s /tmp/091-current/task-091/wps-observations/0003-01-after.json
test -s /tmp/091-current/task-091/wps-observations/0004-01-after.json
gh api -H 'Accept: application/vnd.github+json' /repos/${GITHUB_REPOSITORY}/actions/artifacts/10572233191/zip > /tmp/091-deck.zip
mkdir -p /tmp/091-deck
unzip -q /tmp/091-deck.zip -d /tmp/091-deck
test -s /tmp/091-deck/task-091/wps-observations/0004-01-before.json
test -s /tmp/091-deck/task-091/wps-observations/0004-01-after.json
gh api -H 'Accept: application/vnd.github+json' /repos/${GITHUB_REPOSITORY}/actions/artifacts/10572823026/zip > /tmp/091-pointer.zip
mkdir -p /tmp/091-pointer
unzip -q /tmp/091-pointer.zip -d /tmp/091-pointer
test -s /tmp/091-pointer/task-091/wps-observations/0004-01-after.json
gh api -H 'Accept: application/vnd.github+json' /repos/${GITHUB_REPOSITORY}/actions/artifacts/10574751739/zip > /tmp/091-keyrepeat.zip
mkdir -p /tmp/091-keyrepeat
unzip -q /tmp/091-keyrepeat.zip -d /tmp/091-keyrepeat
test -s /tmp/091-keyrepeat/task-091/wps-observations/0009-01-after.json
test -s /tmp/091-keyrepeat/task-091/wps-trace.jsonl
gh api -H 'Accept: application/vnd.github+json' /repos/${GITHUB_REPOSITORY}/actions/artifacts/10583941746/zip > /tmp/091-delete-repair.zip
mkdir -p /tmp/091-delete-repair
unzip -q /tmp/091-delete-repair.zip -d /tmp/091-delete-repair
test -s /tmp/091-delete-repair/task-091/wps-observations/0013-01-after.json
test -s /tmp/091-delete-repair/task-091/wps-trace.jsonl
gh api -H 'Accept: application/vnd.github+json' /repos/${GITHUB_REPOSITORY}/actions/artifacts/10584667099/zip > /tmp/091-restricted-repair.zip
mkdir -p /tmp/091-restricted-repair
unzip -q /tmp/091-restricted-repair.zip -d /tmp/091-restricted-repair
test -s /tmp/091-restricted-repair/task-091/wps-observations/0009-01-after.json
test -s /tmp/091-restricted-repair/task-091/wps-trace.jsonl
gh api -H 'Accept: application/vnd.github+json' /repos/${GITHUB_REPOSITORY}/actions/artifacts/10585113906/zip > /tmp/091-shape-target.zip
mkdir -p /tmp/091-shape-target
unzip -q /tmp/091-shape-target.zip -d /tmp/091-shape-target
test -s /tmp/091-shape-target/task-091/wps-observations/0013-01-after.json
test -s /tmp/091-shape-target/task-091/wps-observations/0017-01-after.json
test -s /tmp/091-shape-target/task-091/wps-trace.jsonl
gh api -H 'Accept: application/vnd.github+json' /repos/${GITHUB_REPOSITORY}/actions/artifacts/10585727439/zip > /tmp/091-repair-geometry.zip
mkdir -p /tmp/091-repair-geometry
unzip -q /tmp/091-repair-geometry.zip -d /tmp/091-repair-geometry
test -s /tmp/091-repair-geometry/task-091/wps-observations/0009-01-before.json
test -s /tmp/091-repair-geometry/task-091/wps-observations/0009-01-after.json
test -s /tmp/091-repair-geometry/task-091/wps-observations/0010-01-before.json
test -s /tmp/091-repair-geometry/task-091/wps-trace.jsonl
'''
    replay[3]['name'] = 'Replay exact WPS 2019 Step 2 through alias-isolated selector twice'
    replay[3]['run'] = (
        "set -euo pipefail\n"
        "python scripts/replay_091_local_contract.py /tmp/091/task-091/shim-observations/step_0002.json \\\n"
        "  | tee /tmp/091-local-contract-replay.json\n"
        "! grep -F 'pyautogui.click(35, 884)' /tmp/091-local-contract-replay.json\n")
    replay.insert(4, RUN35391431490_MODAL_REPLAY)
    replay.insert(5, RUN35400883826_ENTER_REPLAY)
    replay.insert(6, RUN35404537401_DECK_REPLAY)
    replay.insert(7, RUN35407234122_POINTER_REPLAY)
    replay.insert(8, RUN35411705196_KEYREPEAT_REPLAY)
    replay.insert(9, RUN35439821335_DELETE_REPAIR_REPLAY)
    replay.insert(10, RUN35443356294_RESTRICTED_REPAIR_REPLAY)
    replay.insert(11, RUN35444915125_SHAPE_TARGET_REPLAY)
    replay.insert(12, RUN35448424940_REPAIR_GEOMETRY_REPLAY)
    replay[13]['with']['path'] = '/tmp/091-local-contract-replay.json\n/tmp/run35391431490-modal-regression.json\n/tmp/run35400883826-enter-regression.json\n/tmp/run35404537401-deck-regression.json\n/tmp/run35407234122-pointer-regression.json\n/tmp/run35411705196-keyrepeat-regression.json\n/tmp/run35439821335-delete-repair-regression.json\n/tmp/run35443356294-restricted-repair-regression.json\n/tmp/run35444915125-shape-target-regression.json\n/tmp/run35448424940-repair-geometry-regression.json\n'
    expected['jobs']['final-certification'] = yaml.safe_load(FINAL_CERTIFICATION_JOB_YAML)['final-certification']
    require(len(re.findall(r'(?m)^\s+TASK_ID: [\'"]091[\'"]\s*$', text)) == 1,
            'TASK091_MUST_BE_QUOTED_YAML_STRING')
    normalized_current = normalize(current)
    normalized_expected = normalize(expected)
    if normalized_current != normalized_expected:
        import difflib
        left = yaml.safe_dump(normalized_expected, sort_keys=True).splitlines()
        right = yaml.safe_dump(normalized_current, sort_keys=True).splitlines()
        print('\n'.join(difflib.unified_diff(left, right, fromfile='EXPECTED_WORKFLOW', tofile='CURRENT_WORKFLOW', lineterm='')))
    require(normalized_current == normalized_expected, 'UNEXPECTED_WORKFLOW_SEMANTIC_DELTA')
    unquoted = re.sub(r'(?m)^(\s+TASK_ID:) [\'"]091[\'"]\s*$', r'\1 091', text)
    require(not re.search(r'(?m)^\s+TASK_ID: [\'"]091[\'"]\s*$', unquoted),
            'TASK091_QUOTING_NEGATIVE_TEST_FAILED')


def main():
    require(git('merge-base', BASE, 'HEAD') == BASE, 'BASE_ANCESTRY_MISMATCH')
    require(git('merge-base', CLEAN_BASELINE, 'HEAD') == CLEAN_BASELINE,
            'CLEAN_BASELINE_ANCESTRY_MISMATCH')
    require(git('rev-list', '--count', BASE + '..' + CLEAN_BASELINE) == '3',
            'EXACTLY_THREE_BASELINE_COMMITS_REQUIRED')
    total_commits = int(git('rev-list', '--count', BASE + '..HEAD'))
    require(total_commits >= 253, 'MINIMUM_TWO_HUNDRED_FIFTY_THREE_AUDITED_COMMITS_REQUIRED')
    require(not git('rev-list', '--merges', BASE + '..HEAD'), 'MERGE_COMMITS_FORBIDDEN')
    all_commits = git('rev-list', '--reverse', CLEAN_BASELINE + '..HEAD').splitlines()
    overlay = all_commits[:250]
    post_legacy = all_commits[250:]
    require(len(overlay) == 250, 'EXACTLY_TWO_HUNDRED_FIFTY_REPAIR_COMMITS_REQUIRED')
    allowed_post_scope = {VERIFIER, SHIM, SENIOR_BOARD, SENIOR_TEST}
    approved_post_commit_scopes = {
        'fdd1c8ef17c7f52352b60c1afd7bffca958182a1': {SAFE_HTTP},
        'f60da82e96d92b0de454d9564d860cba56fad563': {SAFE_HTTP},
        '06d8d8f242b0564bf59a5e0112857490fb03be9f': {SAFE_HTTP},
        'c2a0300c589e114645b517f0f4635449e84df9c3': {MANIFEST},
        '4f9aaa2546ba49407c79253742dd55a8aa8f2954': {TRACE_TEST},
        '7d275ed7849d34a0f1fe1e874624c662d37f0d37': {MESH_TEST},
        '3f8e8122aa0de2906c5b969310044a006e48d582': {TRACE_TEST},
        'a1abfc95b29e08a0f75230d98a9bf1d608dbe48c': {GLOBAL_GATE},
        'f6048e4682e76ea8203d8a718e7bc77d61b53cdc': {GLOBAL_GATE},
        '4a74350a8c7d13dc53ad190df0ad2ba53c872cd2': {SHIM},
        'f5d47fcd1f8eacd1e21e168b6650c4700ea96c0c': {SHIM},
        'e9fee7bd29d0542e03d4ebcbe1557abc76914813': {TRACE_TEST},
        '99271dfbfa4a40570afd9d7c6b0bba2c63e3c199': {MESH_TEST},
        '480e5c6456ed65d6bcb6a7b76e2847c56735f5a5': {GLOBAL_GATE},
        '3376e1635d8cc8f149def9a2bdeed6884200b118': {MESH_TEST},
        '99eb0638b1556f420ac5d95fc8eac834dae103b8': {SHIM},
        '94079b5aafae4c5025b61a2c2ebb8a82a25f2b3e': {TRACE_TEST},
        '40f4fce9f180029094e045ea85e8eb2c7f928e43': {MESH_TEST},
        '0dcdd0fb447cd136ad50ddbf063ea0971b172437': {GLOBAL_GATE},
        '812087b8d9fd9bfa73601ca9906ec9e1e7573a92': {TRACE_TEST},
        '4e005f4d34d4227cfc87be631391bec720c07e1a': {GLOBAL_GATE},
        'b2c89a18ae73c374226fd92c45c6309f29ccc092': {SHIM},
        '25dc576f05b14ce25c0efd88590afb42f51c8754': {MESH_TEST},
        'c7a4f8a469908e72785e5972b2838da4ca59e009': {TRACE_TEST},
        '489f30f25cb08a54d1401b914fc734a85d9bd968': {SHIM},
        '8e8a5bbb0b760f772b123a522621064fa1194bfa': {SHIM},
        '44f52e2131c2fe345fcb95fb060b22e178f15bb4': {TRACE_TEST},
        '6725a158fb32c01942923525db845dedaf41897f': {MESH_TEST},
        '65f2b60a1ac4db3e093f113af87ae9e3bdd345b8': {GLOBAL_GATE},
        '2f0114e64912f57c8b9fb035c8103c06ad39d9de': {TRACE_TEST},
        'ef0624c4b00fb2d98da4fe99bc4c1effe38926a1': {TRACE_TEST},
        'd44fa19c1bb78fdfc8eddd769afa5e512a6a5911': {TRACE_TEST},
        '94c6a19f7093ad0db7c57ae200719d579bb86aba': {SHIM},
        'e5288d5f275ecb6d2901e33a78491295dc9e6a5a': {TRACE_TEST},
        'd923d847397a9f3da728685ac496d1a175d58d20': {MESH_TEST},
        '7e5d1d16a34c5c346d4b0059fa8e5f296354dcf0': {SHIM},
        'b7902bd66d8e8a4b4b64cf1a3a632715be1b7f7d': {TRACE_TEST},
        'a07e3a81378356d20e23697a2e92b393689fe8cc': {MESH_TEST},
        'db8505e4cdc2feb63a9276b2e847b024cf0edff0': {GLOBAL_GATE},
        '8fb467bcd9b7074da43617613d86999ac3807e63': {REVIEW_BOARD},
        'c39864b4d2a70f3eb1ffd74ec1c154c976458e69': {ELITE_BOARD},
        'e797bcaa68ad4588b2a2aa5df0737315438db340': {FINAL_BOARD},
        'c803261f5c1e129f1a124489aed5adf44b5038f3': {MESH_TEST},
        'c0eda440c8dc0ad097e7952b67cb8a13cc76f5ff': {ELITE_TEST},
        'c467960a6b56c6691ddb641c97ca1850eeb8f756': {WORKFLOW},
        '3e4516d63648e4781d3e90ce45cb975e6ec23576': {MANIFEST},
        'f1a2a0ada07bc506739a5044b8541ee6381c3c30': {TRACE_TEST},
        '546e8d795a69d94ece35dd258765ead91d7e12c6': {TRACE_TEST},
        '63750ac0fa60bfeb9a2e04b87cc16d1a1978dc8c': {MESH_TEST},
        '66ee832947cd0a4c7732923de68c3539f8b6270d': {TRACE_TEST},
        'f6a0ff18d051d37287476a1b55cbbc45d69dd299': {TRACE_TEST},
        '7421f06fbd19537381b9bb9a97baf0d92f2664d6': {GLOBAL_GATE},
        'b0d4d3c2dcfa0d69316ce4e12cfb8e8249bbe3df': {SHIM},
        '97558261e8e8c889385bfbf602e9711a3ae3bec8': {MESH_TEST},
        '28f22bc8ee1d63fb3877ee75ad0c9ecaae04576a': {TRACE_TEST},
        'acb50a1e0e6539a8cc864ea3f85094f813a1e7d6': {GLOBAL_GATE},
        'c2aa3ca62f7d3d9fd94134218937ffe7ef402342': {SHIM},
        'd9dc51d1b0e9c7024355462c1bd206f6e7950ebc': {MESH_TEST},
        '3c0644d3e58204925b05b5b9174ccd0802047a9f': {TRACE_TEST},
        '11f6296fa0f8ddc65e48df7bfb70bb1745dabe5d': {GLOBAL_GATE},
        'e3ffd84ff7ed55b3db63546f2b75e78950bf0aa4': {SHIM},
        'dec9916247b9151ed7d2183d6e2f2bfe2e465119': {SHIM},
        '7bc52451be12dc964ddeffd9e4f8991285e45b4c': {MESH_TEST},
        'f1a3eb398970683c777e0c37b018ff48db9a36e7': {TRACE_TEST},
        '102705bb2a226a19f6ba3f1bcb60a1b35d645b4a': {GLOBAL_GATE},
        'adc6387dab455fb2032ab65f86aae547186515de': {TRACE_TEST},
        '95a5414c0a12c3c35142464c9560c75cd9970aa1': {TRACE_TEST},
        'db9d0357ea2011315ca6fb1093962a6cb98a4652': {MESH_TEST},
        '94b893aae516662856d850d50b1746378f5a7fa0': {MESH_TEST, TRACE_TEST},
        'be13caf1caa25947ea079a5fadd7a2e712950c0a': {VERIFIER},
        'f6eefc678be0f254606dba0698e5ca23aa398e42': {SHIM, TRACE_TEST},
        '5fb6750da9a63de1a3e3e59d047e5f027a5d7f1c': {GUEST_PROBE, SHIM, TRACE_TEST},
        'd2114604c959587a695619528a72e1dfc810f295': {VERIFIER},
        '35d27d9f8e0e5e180ab2edd6bcdd6f1080191f55': {SHIM},
        '219fb0fda3b8d0de995137847212a7f9e23588e6': {SHIM},
        '64154ecdc784a9b6c170ad8c595b4e17e7d33229': {MESH_TEST},
    }
    for c_node in post_legacy:
        c_files = set(git('diff-tree', '--no-commit-id', '--name-only', '-r', c_node).splitlines())
        exact_scope = approved_post_commit_scopes.get(c_node)
        if exact_scope is not None:
            require(c_files == exact_scope, 'POST_LEGACY_COMMIT_SCOPE_DRIFT:' + c_node)
        else:
            require(c_files and c_files.issubset(allowed_post_scope),
                    'POST_LEGACY_COMMIT_SCOPE_VIOLATION:' + c_node)
    require(overlay[2] == PID_FILTER_COMMIT and overlay[3] == PID_TEST_COMMIT,
            'PID_REPAIR_COMMIT_IDENTITY_MISMATCH')
    require(overlay[6] == WPS_ALIAS_COMMIT and overlay[7] == WPS_ALIAS_TEST_COMMIT
            and overlay[8] == WPS_SWITCH_COMMIT and overlay[9] == WPS_SWITCH_TEST_COMMIT,
            'WPS_ALIAS_REPAIR_COMMIT_IDENTITY_MISMATCH')
    expected_scopes = (VERIFIER, WORKFLOW, LOCAL_VLM, LOCAL_VLM_TEST, VERIFIER, WORKFLOW,
                       LOCAL_VLM, LOCAL_VLM_TEST, TRACE_GATE, TRACE_TEST, VERIFIER, WORKFLOW, VERIFIER, WORKFLOW,
                       VERIFIER, SHIM, MESH_TEST, VERIFIER, TRACE_GATE, TRACE_TEST, VERIFIER, WPS_OBSERVER, TRACE_TEST, VERIFIER, SHIM, MESH_TEST, VERIFIER, SHIM, MESH_TEST, VERIFIER, SHIM, MESH_TEST, VERIFIER, MESH_TEST, VERIFIER, SHIM, MESH_TEST, VERIFIER, SHIM, MESH_TEST, VERIFIER, SHIM, MESH_TEST,
                       (SHIM, MESH_TEST), VERIFIER, TRACE_GATE, TRACE_GATE, WPS_OBSERVER, WPS_OBSERVER,
                       SHIM, TRACE_GATE, MESH_TEST, TRACE_TEST, WORKFLOW, VERIFIER, VERIFIER, TRACE_GATE, VERIFIER, WORKFLOW, VERIFIER, VERIFIER, WORKFLOW, VERIFIER, GUEST_PROBE, WPS_OBSERVER, TRACE_GATE, SHIM, TRACE_TEST, MESH_TEST, WORKFLOW, VERIFIER, TRACE_GATE, TRACE_TEST, VERIFIER, GUEST_PROBE, WPS_OBSERVER, TRACE_GATE, GUEST_PROBE, WPS_OBSERVER, SHIM, MESH_TEST, TRACE_TEST, GUEST_PROBE, WPS_OBSERVER, TRACE_GATE, SHIM, MESH_TEST, TRACE_TEST, WORKFLOW, VERIFIER, MESH_TEST, WORKFLOW, VERIFIER, MESH_TEST, VERIFIER, CONTROL, SHIM, MESH_TEST, WORKFLOW, VERIFIER, WORKFLOW, VERIFIER, WPS_OBSERVER, SHIM, MESH_TEST, WORKFLOW, VERIFIER, WORKFLOW, VERIFIER, GUEST_PROBE, WPS_OBSERVER, SHIM, MESH_TEST, WORKFLOW, VERIFIER, WORKFLOW, VERIFIER, MESH_TEST, WORKFLOW, VERIFIER, MESH_TEST, WORKFLOW, VERIFIER, VERIFIER, MESH_TEST, VERIFIER, SHIM, REVIEW_BOARD, MESH_TEST, WORKFLOW, MESH_TEST, WORKFLOW, MANIFEST, VERIFIER, GUEST_PROBE, WPS_OBSERVER, SHIM, MESH_TEST, MESH_TEST, ELITE_BOARD, ELITE_TEST, WORKFLOW, MANIFEST, VERIFIER, MESH_TEST, VERIFIER, MESH_TEST, VERIFIER, TRACE_GATE, TRACE_TEST, VERIFIER, SHIM, MESH_TEST, WORKFLOW, VERIFIER, SHIM, MESH_TEST, VERIFIER, MESH_TEST, VERIFIER, WORKFLOW, VERIFIER, SHIM, MESH_TEST, WORKFLOW, VERIFIER, SHIM, VERIFIER, SHIM, MESH_TEST, VERIFIER, MESH_TEST, VERIFIER, SHIM, TRACE_TEST, VERIFIER, SHIM, GUEST_PROBE, TRACE_GATE, TRACE_TEST, MESH_TEST, TRACE_TEST, VERIFIER, GUEST_PROBE, TRACE_TEST, VERIFIER, WORKFLOW, VERIFIER, SHIM, MESH_TEST, VERIFIER, WORKFLOW, VERIFIER, WORKFLOW, VERIFIER, SHIM, TRACE_GATE, MESH_TEST, TRACE_TEST, WORKFLOW, VERIFIER, MESH_TEST, VERIFIER, MESH_TEST, VERIFIER, VERIFIER, WORKFLOW, VERIFIER, VERIFIER, TRACE_GATE, TRACE_TEST, VERIFIER, TRACE_GATE, TRACE_TEST, VERIFIER, TRACE_GATE, VERIFIER, WPS_OBSERVER, TRACE_GATE, TRACE_TEST, WORKFLOW, VERIFIER, TRACE_TEST, VERIFIER, SHIM, TRACE_TEST, VERIFIER, TRACE_TEST, VERIFIER, SHIM, TRACE_TEST, VERIFIER, TRACE_TEST, VERIFIER, TRACE_TEST, VERIFIER, SHIM, TRACE_TEST, VERIFIER, TRACE_TEST, VERIFIER, MESH_TEST, SHIM, TRACE_TEST, SENIOR_BOARD, SENIOR_TEST, GLOBAL_GATE, GLOBAL_TEST, MANIFEST, VERIFIER)
    require(overlay[43] == SUPERSEDED_ALT_F4_COMMIT, 'SUPERSEDED_ALT_F4_COMMIT_IDENTITY_MISMATCH')
    for commit, allowed in zip(overlay, expected_scopes):
        actual=set(git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).splitlines())
        wanted={allowed} if isinstance(allowed, str) else set(allowed)
        require(actual == wanted, 'REPAIR_COMMIT_SCOPE_MISMATCH:' + commit)
    parent = CLEAN_BASELINE
    for commit in overlay:
        require(git('rev-parse', commit + '^') == parent, 'REPAIR_HISTORY_NOT_LINEAR')
        parent = commit
    require(not git('diff', '--name-only', '--diff-filter=D', CLEAN_BASELINE, 'HEAD'),
            'REPAIR_DELETION_FORBIDDEN')
    manifest = json.loads(Path('audit/arbm091-final-files.json').read_text())
    changed = set(git('diff', '--name-only', BASE, 'HEAD').splitlines())
    require(changed == set(manifest), 'CHANGED_FILE_ALLOWLIST_MISMATCH')
    require(set(git('diff', '--name-only', CLEAN_BASELINE, 'HEAD').splitlines())
            == {WORKFLOW, VERIFIER, LOCAL_VLM, LOCAL_VLM_TEST, TRACE_GATE, TRACE_TEST, SHIM, MESH_TEST, WPS_OBSERVER, GUEST_PROBE, CONTROL, REVIEW_BOARD, MANIFEST, ELITE_BOARD, ELITE_TEST, SENIOR_BOARD, SENIOR_TEST, GLOBAL_GATE, GLOBAL_TEST, FINAL_BOARD, SAFE_HTTP},
            'REPAIR_TOTAL_SCOPE_MISMATCH')
    exists = subprocess.run(['git', 'cat-file', '-e', PATCH_SOURCE], capture_output=True).returncode == 0
    if exists:
        require(subprocess.run(['git', 'merge-base', '--is-ancestor', PATCH_SOURCE, 'HEAD']).returncode != 0,
                'POLLUTED_SOURCE_HISTORY_IMPORTED')
    dependencies = json.loads(Path('audit/arbm091-dependencies.json').read_text())
    require(dependencies['base_sha'] == BASE and dependencies['historical_commits_imported'] == 0,
            'DEPENDENCY_PROVENANCE_MISMATCH')
    adjustments = json.loads(Path('audit/arbm091-baseline-adjustments.json').read_text())
    patch = json.loads(Path('audit/arbm091-parser-only.patch.json').read_text())
    require(patch['after'] == PATCH_SOURCE
            and hashlib.sha256(patch['patch'].encode()).hexdigest() == patch['patch_sha256'],
            'PARSER_PATCH_PROVENANCE_MISMATCH')
    expected = {row['path']: row['sha256'] for row in dependencies['files']}
    expected.update({row['path']: row['after_sha256'] for row in adjustments})
    expected.update(patch['postimage_sha256'])
    repaired = {LOCAL_VLM: WPS_ALIAS_COMMIT, LOCAL_VLM_TEST: WPS_ALIAS_TEST_COMMIT,
                TRACE_GATE: overlay[218], TRACE_TEST: overlay[243], VERIFIER: overlay[249], WPS_OBSERVER: overlay[217],
                GUEST_PROBE: overlay[183], CONTROL: overlay[95], SHIM: overlay[242], MESH_TEST: overlay[241],
                REVIEW_BOARD: overlay[127], MANIFEST: overlay[248], ELITE_BOARD: overlay[139], ELITE_TEST: overlay[140],
                SENIOR_BOARD: overlay[244], SENIOR_TEST: overlay[245], GLOBAL_GATE: overlay[246], GLOBAL_TEST: overlay[247]}
    for c_node in post_legacy:
        for changed_path in git('diff-tree', '--no-commit-id', '--name-only', '-r', c_node).splitlines():
            if changed_path in repaired:
                repaired[changed_path] = c_node
    for path, wanted in expected.items():
        if path in repaired:
            source = subprocess.check_output(['git', 'show', repaired[path] + ':' + path])
            require(Path(path).read_bytes() == source, 'PID_REPAIR_DRIFT:' + path)
            continue
        require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == wanted,
                'TRANSPLANTED_DEPENDENCY_HASH_MISMATCH:' + path)
    require("hotkey('alt', 'f4')" not in Path(SHIM).read_text(),
            'SUPERSEDED_ALT_F4_REMAINS_IN_FINAL_SHIM')
    verify_workflow_delta()
    print(json.dumps({'status': 'CLEAN_HISTORY_AND_SCOPE_PASS', 'base_sha': BASE,
                      'clean_baseline_sha': CLEAN_BASELINE, 'baseline_commits': 3,
                      'repair_commits': overlay, 'post_legacy_commits': len(post_legacy), 'new_commits': total_commits, 'changed_files': len(changed),
                      'repair_scope': [VERIFIER, WORKFLOW, LOCAL_VLM, LOCAL_VLM_TEST,
                                       TRACE_GATE, TRACE_TEST, SHIM, MESH_TEST, WPS_OBSERVER, GUEST_PROBE, CONTROL, REVIEW_BOARD, MANIFEST, ELITE_BOARD, ELITE_TEST, SENIOR_BOARD, SENIOR_TEST, GLOBAL_GATE, GLOBAL_TEST, FINAL_BOARD], 'official_score_claimed': False}))


if __name__ == '__main__':
    main()