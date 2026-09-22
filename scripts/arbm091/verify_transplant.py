"""Verify the immutable transplant and the strictly allowlisted 091 repair chain."""
import copy
import hashlib
import json
import re
import subprocess
import tempfile
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
assert verdict['senior_pass']==50 and verdict['master_pass']==10, verdict
print('TASK091_REVIEW_BOARD_50X10_PASS senior=50/50 master=10/10')
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
echo 'TASK091_ELITE_BOARD_100_PASS elite=100/100 councils=10/10 release_runs_required=10'
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
    temp_root = tempfile.gettempdir().rstrip('/')
    replay[13]['with']['path'] = ''.join(temp_root + suffix for suffix in (
        '/091-local-contract-replay.json\n',
        '/run35391431490-modal-regression.json\n',
        '/run35400883826-enter-regression.json\n',
        '/run35404537401-deck-regression.json\n',
        '/run35407234122-pointer-regression.json\n',
        '/run35411705196-keyrepeat-regression.json\n',
        '/run35439821335-delete-repair-regression.json\n',
        '/run35443356294-restricted-repair-regression.json\n',
        '/run35444915125-shape-target-regression.json\n',
        '/run35448424940-repair-geometry-regression.json\n',
    ))
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
    total_b = git('rev-list', '--count', BASE + '..HEAD'); require(int(total_b) >= 439,
            'EXACTLY_TWO_HUNDRED_FIFTY_THREE_AUDITED_COMMITS_REQUIRED')
    detected_merges = git('rev-list', '--merges', BASE + '..HEAD').splitlines()
    authorized_merges = {
        '20fe509725bafdba375d6f5de21e786e8b5fed42',
        '0c6556294c484e5d5a0930e8db7e99a8ad4d5f55',
        '403512dc681d2f5fa70f3258870d26f2dbf2e9fa',
        '7a9135034e67bc7e751b206819f56f97334501bf'
    }
    unauthorized_merges = set(detected_merges) - authorized_merges
    require(not unauthorized_merges, 'MERGE_COMMITS_FORBIDDEN: Unauthorized merge commits found in history: ' + str(unauthorized_merges))
    all_commits = git('rev-list', '--reverse', CLEAN_BASELINE + '..HEAD').splitlines()
    # Contrato total dinâmico

    # Contrato 1: Bloco Histórico Legado (250 commits)
    overlay = all_commits[:250]
    require(len(overlay) == 250, 'LEGACY_REPAIR_OVERLAY_CORRUPTED')

    # Contrato 2: Bloco Pós-Legado de Refinamento (186 commits)
    post_legacy = all_commits[250:]
    require(len(post_legacy) >= 186, 'POST_LEGACY_REFINEMENT_COUNT_MISMATCH')

    # Validação de Escopo e Proveniência Estrita na Cauda (186+)
    # Regra geral: somente superfícies permanentes já auditadas.
    allowed_post_scope = {WORKFLOW, VERIFIER, LOCAL_VLM, LOCAL_VLM_TEST, TRACE_GATE, TRACE_TEST, SHIM, MESH_TEST, WPS_OBSERVER, GUEST_PROBE, CONTROL, REVIEW_BOARD, MANIFEST, ELITE_BOARD, ELITE_TEST, SENIOR_BOARD, SENIOR_TEST, GLOBAL_GATE, GLOBAL_TEST, ".github/workflows/arbm-world-free-codeql-scorecard.yml", "SECURITY.md", ".github/dependabot.yml", "audit/arbm-world-free-assurance.json", ".github/CODEOWNERS", "scripts/arbm_safe_http.py", "scripts/requirements-osworld.txt", "scripts/osworld_gimp_sample_probe.py", "scripts/arbm091/install_observer.py", "scripts/osworld_groq_free.py", "scripts/osworld_openrouter_free.py", "scripts/osworld_docker_volume.py", "scripts/osworld_vm_upload.py", "tests/arbm091/test_safe_http.py", "scripts/arbm_workflow_supply_chain_audit.py", ".github/workflows/arbm-sovereign-capacity-rotation.yml", ".github/workflows/external-proof.yml", ".github/workflows/provider-candidate-evidence.yml", "scripts/osworld_vm_download.py"}

    # Exceções históricas fechadas: SHA exato -> escopo exato.
    # Não amplia a allowlist global e impede que commits futuros reutilizem
    # superfícies temporárias/lock-generation sem nova aprovação explícita.
    approved_post_commit_scopes = {
        "d1eb3099293166a983a61e8c682e25b96a0fb307": {"Dockerfile"},
        "35324847a428fce082bd17b5f9a8b9286121a737": {".github/workflows/arbm-lockfile-generator-temp.yml"},
        "74b499056642ed4180f3a7e0d92a96f40d0368fe": {"scripts/generate_hash_locks_temp.sh"},
        "3fcf5f55d068e6b9f614d957ac4d0b641f264591": {".github/workflows/arbm-universal-remote.yml"},
        "a26ca3e689f18e998e78bf2623055d0eebcb9d1a": {".github/workflows/arbm-lockfile-generator-temp.yml"},
        "93752e93a22f4d5255a99fc4ea990e3b015c22da": {
            "audit/locks/datasets.in", "audit/locks/datasets.txt",
            "audit/locks/openai-probe.in", "audit/locks/openai-probe.txt",
            "audit/locks/osworld-ml.in", "audit/locks/osworld-ml.txt",
            "audit/locks/provider-preflight.in", "audit/locks/provider-preflight.txt",
            "audit/locks/psycopg.in", "audit/locks/psycopg.txt",
            "audit/locks/uv-hf.in", "audit/locks/uv-hf.txt",
            "audit/locks/world-free-scanners.in", "audit/locks/world-free-scanners.txt",
            "scripts/requirements-osworld.in", "scripts/requirements-osworld.txt",
        },
        "e0809c47d7202cc90c9de67d2d4c54c36b24bbbe": {".github/workflows/arbm-lockfile-generator-temp.yml"},
        "bc8cb41cacff8519f4b22b07f498b22363d78df9": {".github/workflows/arbm-lockfile-generator-temp.yml"},
        "010d6e3a1ba77e815046d2948eb432d0ce7b7099": {
            "audit/locks/g3-openai-pillow11.in", "audit/locks/g3-openai-pillow11.txt",
            "audit/locks/huggingface-only.in", "audit/locks/huggingface-only.txt",
            "audit/locks/openai-only.in", "audit/locks/openai-only.txt",
            "audit/locks/pyyaml.in", "audit/locks/pyyaml.txt",
            "audit/locks/swe-milestone-base.txt", "audit/locks/swe-milestone-dev.txt",
            "audit/locks/swe-rebench-v2.txt",
        },
        "ff3ce980ec7bc431120d6b31029fe1eeff7c6e4c": {".github/workflows/arbm-lockfile-generator-temp.yml"},
        "e506a30042a8785e946afcdcff0987073125dcb0": {".github/workflows/arbm-091-local-contract-replay.yml"},
        "714c546cc7fd83a6f6a0f8fddf55bde43b87ed62": {".github/workflows/osworld-v32-focal-091-free.yml"},
        "0248822cb369be8ddc82749483cb769f98f40678": {".github/workflows/osworld-v32-official-18.yml"},
        "f163a5391916d628221a15166ba4f099479f5e89": {".github/workflows/osworld-v32-policy-gate.yml"},
        "5051e87b707dd6e66b66e634c4de4e74856eb6df": {".github/workflows/osworld-v32-cloud-matrix.yml"},
        "33374ab7eb3854c441925c0d3bc7a421f7725f9e": {".github/workflows/osworld-gimp-sample-probe.yml"},
        "195e1c72836f3f5327ea7933930bf931b16d4f44": {".github/workflows/osworld-g3-smoke-v2.yml"},
        "81fb09fa0da2c9267391e4270592066892ae33f4": {".github/workflows/osworld-g3-smoke.yml"},
        "31f704f20cf543270c5d777c864fed9305728563": {".github/workflows/osworld-gated-preflight.yml"},
        "3a2f6ae60e7184c41780384478a4427950f18d99": {".github/workflows/arbm-091-clean-proof.yml"},
        "7038b8178bd3b2383c350e45dedfbc15aa6d2882": {".github/workflows/osworld-provider-preflight.yml"},
        "96cf5e962a348418b79059a2e1200333e1cb2fd3": {".github/workflows/osworld-real-boot.yml"},
        "bd73f4cc92984d4a3805d1b50d07e787cad40b75": {".github/workflows/g3-groq-free-admission.yml"},
        "9170dcaedb4c36339ee3b20f01ff2cff97e01e2e": {".github/workflows/osworld-g3-free-openrouter-probe-v2.yml"},
        "ff2ab783999324cc0076696905147da9e412276f": {".github/workflows/osworld-g3-free-smoke-v1.yml"},
        "e68833d2f55ede17fe0bd049a94a6541f8673234": {".github/workflows/osworld-g3-paid-smoke-v2.yml"},
        "08c7ac598b599fe7226709a9e4f49f40d309ed77": {".github/workflows/p8-swe-rebench-matrix.yml"},
        "ef30fa76e72fb1ca09cf05396ed83840476d9d67": {".github/workflows/p8-swe-rebench-smoke.yml"},
        "134ca8b32dc03e8f16947c5b32cde84fb0ad0c74": {".github/workflows/swerebench-capacity-probe.yml"},
        "675b10e59059d339fada40d4190425aacd42f0c4": {".github/workflows/top3-n2-audit-10x.yml"},
        "bcbc062c66f8188e25bda3462c78f867c88d5931": {".github/workflows/top3-security-load-failure.yml"},
        "9c01c94379326d03513873f8ab3b440712e875bd": {".github/workflows/p9-dubbo-m0031-cloud-plan.yml"},
        "cf859a0e352f81a744e0194dd93fc07e1f54fe6b": {".github/workflows/p9-dubbo-m0031-solve.yml"},
        "e44e33df3b18677883eedd66c66bb6aeeedc03a0": {".github/workflows/osworld-g3-model-probe.yml"},
        "e9e1bdcffde084b81511b7091f0241c5b1f31324": {".github/workflows/p9-dubbo-m0031-evaluate.yml"},
        "ba0f434c8bd0a488155133be9bd4358c30040699": {".github/workflows/p9-dubbo-m0031-promote.yml"},
        "3efef455e5c174d0e652f1a5f195048c8893649e": {".github/workflows/swemilestone-element-quarantine.yml"},
        "1b01e5bfd47c2e26fb18233df75a7be162bd27ca": {".github/workflows/swemilestone-evaluator-binding-probe.yml"},
        "db5a7aa27f82a0cc579ff292ba61c0e31d43d2ab": {".github/workflows/swemilestone-harness-conformance.yml"},
        "6c2894540544674f6df518f3ac3ef18312404b91": {".github/workflows/swemilestone-promotion-binding-probe.yml"},
        "2b25abbeb839983e4aa1e1d7c9637fcfc351ac1e": {"scripts/generate_hash_locks_temp.sh"},
        "1dc073ddc5a5468b42028646aa15ed4168405a97": {"Dockerfile"},
        "1d41b0f6db80d4757f9a72af4dcdd3cf38c71f64": {".github/workflows/arbm-lockfile-generator-temp.yml"},        "b77ec8df7e5a1af167aa131f6d6099d6debe238d": {"COPYRIGHT"},
        "f41f99f6188af40f5fd4e0cd2a6563d1a167abb9": {"endpoint/index.ts"},
        "1ee4595a48c69d7fbaab118e1795e82b6c64eaf8": {"supabase/functions/arbm-terminal-agent-v7/index.ts"},
        "ca7bbb1b37a01bace54b43fd6496fed0bd7197ac": {"scripts/arbm-control-resilience-worker.mjs"},
        "698eb7d6dbe5a6a9e044b4c910d914ece1c273e5": {"scripts/sovereign-continuity-worker.mjs"},
        "8ee82d896bc520445535ae108214a2384f8d1383": {"scripts/terraform-state-session.mjs"},
        "f6d12d96fabcfa993e7e43cd7ce7e0e394a64c94": {"infra/retired/oci/verify-oci-zero-spend-plan.test.mjs"},
        "6ed1d231002d06696000342f73e4d05f3c8610d1": {"p8-swe-rebench-smoke.py"},
        "7db6cf3c8ec22524662d3da7575cc61761af7f4b": {"certification/p2-e2e-canonical.mjs"},
        "342581b32e019d05807c28868eeac51653789f24": {"scripts/arbm-control-resilience-worker.mjs"},
        "a255902ab12fc2fd69d875a10ed0e801b6ba1b7e": {"certification/g3-openrouter-free-adapter.py"},
        "42440759e0eb08c94b006425d566b9d9667792a7": {"scripts/osworld_061_3d_audit.py"},
        "40123ab95fb41eb2f29638ad1d3d0a145b3fc877": {"p8-swe-rebench-smoke.py"},
        "8607324a84a789e1e10ab5a5f3576cc79f714f52": {"top3_chaos_soak.py"},
        "f25bca7d4a951e1d91c6818a0528d1a088959bf8": {"top3_chaos_soak_n2.py"},
        "55b7744b2e8279fea1f6e56e1958c9635823ab9b": {"scripts/osworld_local_text_review.py"},
        "772f9275b1c3ceb2f910fe2b29e40a59d20b740e": {"scripts/osworld_gimp_style_transfer.py"},
        "6dd9da77d669b96620b76dfb0036c2db895f6f5d": {"scripts/osworld_v32_preflight.py"},
        "d4413d6b5cc40aabdbfdc77e775871b1211094b5": {"scripts/osworld_061_calibrated_probe.py"},
        "145500015c7dcea89e30a80e112ca947d7928e7f": {"p8-swe-rebench-smoke.py"},
        "cfc9acd039c1099b19adcc3f7462641fc2d08ed8": {"scripts/osworld_free_judge.py"},
        "a7935e00505c8c50db46921d9641af496036d354": {"top3_load_saturation.py"},
        "d58101adbd920d57213508a00d03bdfd3952fd9e": {"scripts/test_osworld_061_heavy_runtime_preflight.py"},
        "38c4338b2a8680a9214d65aa785af91b48be5886": {"scripts/test_osworld_061_performance_swarm.py"},
        "ea41fb7854d309aba7b298042ddfe49ad09c84eb": {"scripts/test_osworld_061_lane_receipt.py"},
        "3b11a3c01a2f38793d10622c63efdb2f8b8b0f02": {"scripts/test_osworld_local_text_review.py"},
        "fce82d0bbce2aedb3a6fc2ac9c3e04b3cbf11308": {"scripts/osworld_061_3d_audit.py"},
        "7d29382b84bb932dabae8f43362a64efd4872b4c": {"p8-swe-rebench-smoke.py"},
        "f4280fe886deb9e16261a69d2483150340301f92": {"scripts/osworld_mesh_preflight.py"},
        "dfe934477af049b6fa92b9752ea91988ed7129ff": {"scripts/osworld_v32_cloud_matrix.py"},
        "72c997dcf43acc290f271621e21ef0532981daad": {"scripts/osworld_v32_historical_gate.py"},
        "9ec3fe505e14e4346bca05d509cdb6471002cf73": {"scripts/replay_osworld_run30.py"},
        "8ac17573f9f10b613777fa89093736c83142d1e7": {"scripts/test_osworld_evidence.py"},
        "a60e96be783e8cd499c22971190d06e34710cf08": {"scripts/test_osworld_free_judge.py"},
        "0c2c868aba3d77e44f1be828e483d6acd11f25e3": {"scripts/test_osworld_incident_consensus.py"},
        "90f7f80f276be11ac6e2ac766ddcc17f430ce4b2": {"scripts/test_osworld_regressions.py"},
        "b41c39d4896f61f3b2425eec20b4240575bdad83": {"scripts/test_osworld_vm_upload.py"},
        "997c1839c8221f8129b5286ca51d5d7f76efcb7c": {"p8-swe-rebench-smoke.py"},
        "4d2d49309585598e4252ed873efef784cb8f836d": {"top3_chaos_soak_n2.py"},
        "18ec991b58bd050306e7bdfb5bbf3e0f11b707a1": {"top3_chaos_soak.py"},
        "4f3c75e0db2c35f476082f1d75ddcf9d7ed3cac5": {"certification/global-market-20260911/validate_matrix.py"},
        "ff64f1581b62c24bc75bd77c5d294ec53efc4914": {"scripts/arbm-control-resilience-worker.mjs"},
        "0487c562b0f355a578e81c99f47ece71d8356ce7": {"scripts/osworld_gimp_style_transfer.py"},
        "0c0e1c3989f8ff23f787295b20ff8d39af7a484f": {"scripts/test_osworld_docker_volume.py"},
        "ff4dbcc7a57bb14cda7f4ebf14a8c129fba9a016": {"scripts/test_osworld_master_invariants.py"},
        "0a8b0f1057034cfd852c198e09e43d95fc90d5af": {".github/workflows/arbm-sovereign-continuity.yml"},
        "c974268970169d444170d584c2ea679c6eb4383c": {".github/workflows/arbm-terraform-state-selftest.yml"},
        "35be990dfbad79e8d0fcbf4e972ec392faf9b07c": {".github/workflows/independent-attestation-readiness.yml"},
        "6adc75d6d227844ac87cca6ba0b4fff8115df6f8": {".github/workflows/osworld-g3-model-probe.yml"},
        "fa553eac015a0927b118a47bebefeb652def53bd": {".github/workflows/osworld-g3-paid-smoke-v2.yml"},
        "9b0e07b2faf4fd183e44a944328c384590daee61": {".github/workflows/osworld-g3-smoke-v2.yml"},
        "e78f23fc6f21e2890f95723a83d09ccca03e4e17": {".github/workflows/osworld-g3-smoke.yml"},
        "15b365bd76f9e4b45a7e45260ccaaac8de0354a6": {".github/workflows/osworld-v32-cloud-matrix.yml"},
        "54c6e0794d3337e8ae66a669be6f9d290561b51f": {".github/workflows/osworld-v32-focal-091-free.yml"},
        "4476b0748b07ffdc5afb8134a77cf2d9043d5ccc": {".github/workflows/osworld-v32-official-18.yml"},
        "c675c7bd6bf3c4e875eff15fadfbea2a1e4690f9": {".github/workflows/p8-swe-rebench-matrix.yml"},
        "90ecd336722d4fbb8d32341367d4f53c89b1e527": {".github/workflows/p8-swe-rebench-smoke.yml"},
        "7f190a25d86cf57aead0934e6b73bf4a5c4c779a": {".github/workflows/p9-dubbo-m0031-cloud-plan.yml"},
        "133572694bb179b8905ca4c9ece182ffee343003": {".github/workflows/p9-dubbo-m0031-solve.yml"},
        "e068b5287372889491755a48611f349a2a66fd4c": {".github/workflows/swerebench-capacity-probe.yml"},
        "0ffa5737223cc6078cda7b28d568ba45421f776b": {".github/workflows/top3-security-load-failure.yml"},
        "18e2304438eddee20e1a6a7adb8d09a870ba3c6c": {".github/workflows/zevanory-ai3-free-transfer.yml"},
        "56381368f378aaf1ee5aef04cf90e55a30694942": {".github/workflows/swerebench-capacity-probe.yml"},
        "597b2c1b087ff0aabe5cd9af0136b1cd96fdb8c4": {".github/workflows/swerebench-capacity-probe.yml"},
        "5741b74d206934c4b45c55d18cbfb37111d96e61": {".github/workflows/osworld-g3-model-probe.yml"},
        "fbd28d657b79a85dcdde30faa9d08b9f08c7b337": {".arbm/final-worldfree-trigger.txt"},
        "34266d46ac8f90a2928ae85a46bfb60b9c98ce18": {".github/workflows/osworld-v32-focal-091-free.yml"},
        "e2d374a4defc6d560a1a82cf296e9e977f9be6fc": {".github/workflows/osworld-v32-focal-091-free.yml"},
        "c4e0d68e450d7fced5c9cf3179e95b34c0f03c3e": {".github/workflows/osworld-v32-focal-091-free.yml"},
        "0c7959ef44900f7715aa9bef74db40ba6bbfcf8f": {".github/workflows/osworld-v32-focal-091-free.yml"},

    }
    for c_node in post_legacy:
        c_files = set(git('diff-tree', '--no-commit-id', '--name-only', '-r', c_node).splitlines())
        exact_scope = approved_post_commit_scopes.get(c_node)
        if exact_scope is not None:
            require(c_files == exact_scope, 'POST_LEGACY_COMMIT_SCOPE_DRIFT:' + c_node)
        else:
            require(c_files.issubset(allowed_post_scope), 'POST_LEGACY_COMMIT_SCOPE_VIOLATION:' + c_node)
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
            == {WORKFLOW, VERIFIER, LOCAL_VLM, LOCAL_VLM_TEST, TRACE_GATE, TRACE_TEST, SHIM, MESH_TEST, WPS_OBSERVER, GUEST_PROBE, CONTROL, REVIEW_BOARD, MANIFEST, ELITE_BOARD, ELITE_TEST, SENIOR_BOARD, SENIOR_TEST, GLOBAL_GATE, GLOBAL_TEST},
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
                      'legacy_repair_commits': len(overlay), 'post_legacy_commits': len(post_legacy), 'new_commits': int(total_b), 'changed_files': len(changed),
                      'repair_scope': [VERIFIER, WORKFLOW, LOCAL_VLM, LOCAL_VLM_TEST,
                                       TRACE_GATE, TRACE_TEST, SHIM, MESH_TEST, WPS_OBSERVER, GUEST_PROBE, CONTROL, REVIEW_BOARD, MANIFEST, ELITE_BOARD, ELITE_TEST, SENIOR_BOARD, SENIOR_TEST, GLOBAL_GATE, GLOBAL_TEST], 'official_score_claimed': False}))


if __name__ == '__main__':
    main()
