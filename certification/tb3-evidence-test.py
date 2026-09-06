import json, pathlib, subprocess, sys, tempfile

TASKS = [
    'terminal-bench/atrx-vep-crispr',
    'terminal-bench/batched-eval-parity',
    'terminal-bench/biped-contact-dynamics',
]


def make_trial(root, task, rep, baseline):
    trial = pathlib.Path(root) / f'job-{rep}' / f'trial-{rep}'
    (trial / 'artifacts').mkdir(parents=True)
    meta = {'steps': [{'step': 1, 'command': 'COMPLETE', 'returnCode': 0}]} if baseline else {
        'verifyStart': 19, 'steps': [{'step': 19, 'command': 'test -e /app/out', 'returnCode': 0}],
        'verificationSeen': True,
    }
    result = {'task_name': task, 'agent_result': {'metadata': meta},
              'verifier_result': {'rewards': {'reward': 0}}, 'exception_info': None}
    (trial / 'result.json').write_text(json.dumps(result), encoding='utf-8')
    status = 'failed' if baseline else 'success'
    manifest = [{'source': '/app/out', 'status': status}]
    (trial / 'artifacts' / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')


def run(*args):
    return subprocess.run([sys.executable, *args], check=True, capture_output=True, text=True)

with tempfile.TemporaryDirectory() as td:
    base = pathlib.Path(td)
    evidence = base / 'evidence'
    evidence.mkdir()
    for idx, task in enumerate(TASKS):
        v1, v2 = base / f'v1-{idx}', base / f'v2-{idx}'
        for rep in range(1, 4):
            make_trial(v1, task, rep, True)
            make_trial(v2, task, rep, False)
        out = evidence / f'task-{idx}.json'
        run('certification/tb3-paired-evidence.py', '--task', task,
            '--baseline-root', str(v1), '--candidate-root', str(v2), '--output', str(out))
        data = json.loads(out.read_text(encoding='utf-8'))
        assert data['failureModes']['baseline'] == {
            'premature_completion': 3, 'missing_required_output': 3, 'no_final_verification': 3}
        assert data['failureModes']['candidate'] == {
            'premature_completion': 0, 'missing_required_output': 0, 'no_final_verification': 0}
    aggregate = base / 'aggregate.json'
    run('certification/tb3-aggregate-promotion-evidence.py', '--root', str(evidence),
        '--regression-result', 'success', '--paired-result', 'success', '--output', str(aggregate))
    merged = json.loads(aggregate.read_text(encoding='utf-8'))
    assert len(merged['baselineTrials']) == 9 and len(merged['candidateTrials']) == 9
    assert merged['failureModes']['baseline']['missing_required_output'] == 9
    assert merged['failureModes']['candidate']['missing_required_output'] == 0
print('TB3_EVIDENCE_TEST_PASS')
