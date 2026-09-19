import json
import pathlib
import re
import subprocess

deep=json.loads(pathlib.Path('deep-swe/tasks/manifest.json').read_text())
assert deep['task_count']==113
tb=pathlib.Path('terminal-bench/leaderboard/src/leaderboard/ci/static_analysis.py').read_text()
assert re.search(r'EXPECTED_TASK_COUNT\s*=\s*89',tb)
atlas=pathlib.Path('swe-atlas/golden_tests.py').read_text()
assert 'assert len(TASKS) == 124' in atlas
refs={
  'deep-swe':subprocess.check_output(['git','-C','deep-swe','rev-parse','HEAD'],text=True).strip(),
  'terminal-bench-2-1':subprocess.check_output(['git','-C','terminal-bench','rev-parse','HEAD'],text=True).strip(),
  'swe-atlas-qna':subprocess.check_output(['git','-C','swe-atlas','rev-parse','HEAD'],text=True).strip(),
}
evidence={'schema':'arbm-coding-agent-index-v1.4-preflight','tasks':326,'trialsRequired':978,'trialPolicy':'3_per_task','antiCherryPick':True,'refs':refs,'state':'READY_FOR_AGENT_INFERENCE'}
pathlib.Path('coding-agent-index-preflight.json').write_text(json.dumps(evidence,indent=2)+'\n')
print(json.dumps(evidence))
