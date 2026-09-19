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
deck['deck_file']={'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                   'sha256':'a'*64,'size':1234,'mtime_ns':1}
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
deck['deck_file']={'path':'/home/user/Desktop/Operating_Committee_Rebaseline_Draft.pptx',
                   'sha256':'a'*64,'size':1234,'mtime_ns':1}
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
    'name': 'Replay run 35411705196 WPS key-repeat corruption regression',
    'shell': 'bash',
    'run': '''set -euo pipefail
TASK_ID=091 ZERO_SPEND_MODE=HARD PYTHONPATH=scripts python - <<'PY' | tee /tmp/run35411705196-keyrepeat-regression.json
import json
from pathlib import Path
import osworld_free_mesh_shim as shim

root=Path('/tmp/091-keyrepeat/task-091')
corrupt=json.loads((root/'wps-observations/0009-01-after.json').read_text())
assert corrupt['deck_file']['sha256'] != '4c9c57567fa8f4bd81175dbd3d1b2ea40f0ad1ff8689ca47e1cbd001da637f5b'
slide1=corrupt['deck_slide_text']['1']
assert 'OOperating' in slide1 and 'PPPPPPack' in slide1 and 'RRecover' in slide1, slide1

trace=[json.loads(line) for line in (root/'wps-trace.jsonl').read_text().splitlines() if line.strip()]
selected=next(row['after']['screenshot_sha256'] for row in trace
              if row.get('step')==6 and row.get('substep')==1)
edited=next(row['after']['screenshot_sha256'] for row in trace
            if row.get('step')==7 and row.get('substep')==4)
assert selected != edited

corrupt['screenshot_sha256']=next(row['after']['screenshot_sha256'] for row in trace
                                  if row.get('step')==9 and row.get('substep')==1)
state={'owned':True,'anchored':True,'slide':1,'spatial_index':0,
       'pending_edit':{'slide':1,'old':'Growth Plan Draft',
                       'new':'H2 Operating Committee Pack\\nStabilize-and-Recover Rebaseline',
                       'stage':'save-issued',
                       'target':{'label':'Growth Plan Draft','role':'task091-canonical-point',
                                 'bbox':[744,334,2,2],'cx':745,'cy':335,
                                 'source':'task091-pptx-canonical','slide':1},
                       'before_old_count':1,'before_new_count':0,
                       'before_deck_sha256':'4c9c57567fa8f4bd81175dbd3d1b2ea40f0ad1ff8689ca47e1cbd001da637f5b',
                       'selected_screenshot_sha256':selected,
                       'edited_screenshot_sha256':edited,
                       'verify_attempts':0}}
task=('You are Maya Lin, Business Operations Manager at Northstar Cloud. '
      'The COO has asked you to rebaseline the H2 Operating Committee pack. '
      'The draft deck Operating_Committee_Rebaseline_Draft.pptx is open. '
      'Reforecast_Model_H2.xlsx is the source of truth.')
repair=shim.next_091_specialist_action(task,'WPS Presentation','',state,corrupt)
assert repair['action']=='exec', repair
assert repair['command']=='pyautogui.doubleClick(745, 335, interval=0.08)', repair
assert repair['target']['source']=='task091-pptx-canonical', repair
assert state['pending_edit']['repair_attempts']==1, state['pending_edit']
assert state['pending_edit']['repair_before_deck_sha256']==corrupt['deck_file']['sha256']
assert shim.TASK091_TYPE_INTERVAL >= 0.02
assert shim.TASK091_REPAIR_TYPE_INTERVAL >= 0.05
print(json.dumps({'status':'PASS','corpus_run':'35411705196',
                  'old_failure':'TASK091_EDIT_NOT_VERIFIED',
                  'detected':'saved-key-repeat-corruption',
                  'bounded_repair':1,'zero_spend':'HARD'},sort_keys=True))
print('RUN35411705196_KEYREPEAT_REGRESSION=PASS')
PY
grep -F 'RUN35411705196_KEYREPEAT_REGRESSION=PASS' /tmp/run35411705196-keyrepeat-regression.json
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
    expected['jobs']['focal-091']['env']['TASK_ID'] = '091'
    expected['jobs']['focal-091']['steps'].insert(1, ENVIRONMENT_PREFLIGHT)
    expected['jobs']['proof-tests']['steps'][1]['run'] = (
        'python -m pip install -r scripts/requirements-osworld.txt\n'
        'python -m pip install PyYAML==6.0.2\n')
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
    replay[9]['with']['path'] = '/tmp/091-local-contract-replay.json\n/tmp/run35391431490-modal-regression.json\n/tmp/run35400883826-enter-regression.json\n/tmp/run35404537401-deck-regression.json\n/tmp/run35407234122-pointer-regression.json\n/tmp/run35411705196-keyrepeat-regression.json\n'
    require(len(re.findall(r'(?m)^\s+TASK_ID: [\'"]091[\'"]\s*$', text)) == 1,
            'TASK091_MUST_BE_QUOTED_YAML_STRING')
    require(normalize(current) == normalize(expected), 'UNEXPECTED_WORKFLOW_SEMANTIC_DELTA')
    unquoted = re.sub(r'(?m)^(\s+TASK_ID:) [\'"]091[\'"]\s*$', r'\1 091', text)
    require(not re.search(r'(?m)^\s+TASK_ID: [\'"]091[\'"]\s*$', unquoted),
            'TASK091_QUOTING_NEGATIVE_TEST_FAILED')


def main():
    require(git('merge-base', BASE, 'HEAD') == BASE, 'BASE_ANCESTRY_MISMATCH')
    require(git('merge-base', CLEAN_BASELINE, 'HEAD') == CLEAN_BASELINE,
            'CLEAN_BASELINE_ANCESTRY_MISMATCH')
    require(git('rev-list', '--count', BASE + '..' + CLEAN_BASELINE) == '3',
            'EXACTLY_THREE_BASELINE_COMMITS_REQUIRED')
    require(git('rev-list', '--count', BASE + '..HEAD') == '110',
            'EXACTLY_ONE_HUNDRED_TEN_AUDITED_COMMITS_REQUIRED')
    require(not git('rev-list', '--merges', BASE + '..HEAD'), 'MERGE_COMMITS_FORBIDDEN')
    overlay = git('rev-list', '--reverse', CLEAN_BASELINE + '..HEAD').splitlines()
    require(len(overlay) == 107, 'EXACTLY_ONE_HUNDRED_SEVEN_REPAIR_COMMITS_REQUIRED')
    require(overlay[2] == PID_FILTER_COMMIT and overlay[3] == PID_TEST_COMMIT,
            'PID_REPAIR_COMMIT_IDENTITY_MISMATCH')
    require(overlay[6] == WPS_ALIAS_COMMIT and overlay[7] == WPS_ALIAS_TEST_COMMIT
            and overlay[8] == WPS_SWITCH_COMMIT and overlay[9] == WPS_SWITCH_TEST_COMMIT,
            'WPS_ALIAS_REPAIR_COMMIT_IDENTITY_MISMATCH')
    expected_scopes = (VERIFIER, WORKFLOW, LOCAL_VLM, LOCAL_VLM_TEST, VERIFIER, WORKFLOW,
                       LOCAL_VLM, LOCAL_VLM_TEST, TRACE_GATE, TRACE_TEST, VERIFIER, WORKFLOW, VERIFIER, WORKFLOW,
                       VERIFIER, SHIM, MESH_TEST, VERIFIER, TRACE_GATE, TRACE_TEST, VERIFIER, WPS_OBSERVER, TRACE_TEST, VERIFIER, SHIM, MESH_TEST, VERIFIER, SHIM, MESH_TEST, VERIFIER, SHIM, MESH_TEST, VERIFIER, MESH_TEST, VERIFIER, SHIM, MESH_TEST, VERIFIER, SHIM, MESH_TEST, VERIFIER, SHIM, MESH_TEST,
                       (SHIM, MESH_TEST), VERIFIER, TRACE_GATE, TRACE_GATE, WPS_OBSERVER, WPS_OBSERVER,
                       SHIM, TRACE_GATE, MESH_TEST, TRACE_TEST, WORKFLOW, VERIFIER, VERIFIER, TRACE_GATE, VERIFIER, WORKFLOW, VERIFIER, VERIFIER, WORKFLOW, VERIFIER, GUEST_PROBE, WPS_OBSERVER, TRACE_GATE, SHIM, TRACE_TEST, MESH_TEST, WORKFLOW, VERIFIER, TRACE_GATE, TRACE_TEST, VERIFIER, GUEST_PROBE, WPS_OBSERVER, TRACE_GATE, GUEST_PROBE, WPS_OBSERVER, SHIM, MESH_TEST, TRACE_TEST, GUEST_PROBE, WPS_OBSERVER, TRACE_GATE, SHIM, MESH_TEST, TRACE_TEST, WORKFLOW, VERIFIER, MESH_TEST, WORKFLOW, VERIFIER, MESH_TEST, VERIFIER, CONTROL, SHIM, MESH_TEST, WORKFLOW, VERIFIER, WORKFLOW, VERIFIER, WPS_OBSERVER, SHIM, MESH_TEST, WORKFLOW, VERIFIER)
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
            == {WORKFLOW, VERIFIER, LOCAL_VLM, LOCAL_VLM_TEST, TRACE_GATE, TRACE_TEST, SHIM, MESH_TEST, WPS_OBSERVER, GUEST_PROBE, CONTROL},
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
                TRACE_GATE: overlay[84], TRACE_TEST: overlay[87], WPS_OBSERVER: overlay[102],
                GUEST_PROBE: overlay[82], CONTROL: overlay[95], SHIM: overlay[103], MESH_TEST: overlay[104]}
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
                      'repair_commits': overlay, 'new_commits': 110, 'changed_files': len(changed),
                      'repair_scope': [VERIFIER, WORKFLOW, LOCAL_VLM, LOCAL_VLM_TEST,
                                       TRACE_GATE, TRACE_TEST, SHIM, MESH_TEST, WPS_OBSERVER, GUEST_PROBE, CONTROL], 'official_score_claimed': False}))


if __name__ == '__main__':
    main()
