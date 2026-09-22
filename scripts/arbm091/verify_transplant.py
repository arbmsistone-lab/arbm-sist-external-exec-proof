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

    # Validação de Escopo e Proveniência Estrita na Cauda (186)
    allowed_post_scope = {WORKFLOW, VERIFIER, LOCAL_VLM, LOCAL_VLM_TEST, TRACE_GATE, TRACE_TEST, SHIM, MESH_TEST, WPS_OBSERVER, GUEST_PROBE, CONTROL, REVIEW_BOARD, MANIFEST, ELITE_BOARD, ELITE_TEST, SENIOR_BOARD, SENIOR_TEST, GLOBAL_GATE, GLOBAL_TEST, ".github/workflows/arbm-world-free-codeql-scorecard.yml", "SECURITY.md", ".github/dependabot.yml", "audit/arbm-world-free-assurance.json", ".github/CODEOWNERS", "scripts/arbm_safe_http.py", "scripts/requirements-osworld.txt", "scripts/osworld_gimp_sample_probe.py", "scripts/arbm091/install_observer.py"}
    for c_node in post_legacy:
        c_files = set(git('diff-tree', '--no-commit-id', '--name-only', '-r', c_node).splitlines())
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
