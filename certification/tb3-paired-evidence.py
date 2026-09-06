import argparse, glob, json, os


def trial_failure_modes(result_path, data):
    meta = ((data.get('agent_result') or {}).get('metadata') or {})
    steps = meta.get('steps') or []
    verify_start = int(meta.get('verifyStart') or 19)
    premature = any(str(s.get('command')) == 'COMPLETE' and int(s.get('step') or 0) < verify_start for s in steps)
    no_verify = meta.get('verificationSeen') is not True
    manifest_path = os.path.join(os.path.dirname(result_path), 'artifacts', 'manifest.json')
    missing_output = False
    if os.path.exists(manifest_path):
        try:
            manifest = json.load(open(manifest_path, encoding='utf-8'))
            missing_output = any(x.get('status') == 'failed' for x in manifest if x.get('source') != '/logs/artifacts')
        except (OSError, json.JSONDecodeError):
            missing_output = True
    return {
        'premature_completion': int(premature),
        'missing_required_output': int(missing_output),
        'no_final_verification': int(no_verify),
    }


def load_trials(root, task):
    rows, modes = [], {'premature_completion': 0, 'missing_required_output': 0, 'no_final_verification': 0}
    for path in sorted(glob.glob(os.path.join(root, '**', 'result.json'), recursive=True)):
        try:
            data = json.load(open(path, encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get('task_name') != task or 'verifier_result' not in data:
            continue
        rewards = (data.get('verifier_result') or {}).get('rewards') or {}
        reward = float(rewards.get('reward') or 0)
        rows.append({'task': task, 'reward': reward, 'exception': bool(data.get('exception_info'))})
        observed = trial_failure_modes(path, data)
        for key, value in observed.items():
            modes[key] += value
    for idx, row in enumerate(rows, 1):
        row['rep'] = idx
    return rows, modes


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--task', required=True)
    p.add_argument('--baseline-root', default='jobs-v1')
    p.add_argument('--candidate-root', default='jobs-v2')
    p.add_argument('--output', required=True)
    a = p.parse_args()
    baseline, baseline_modes = load_trials(a.baseline_root, a.task)
    candidate, candidate_modes = load_trials(a.candidate_root, a.task)
    if len(baseline) != 3 or len(candidate) != 3:
        raise SystemExit(f'expected_3x3_got_{len(baseline)}_{len(candidate)}')
    out = {
        'baselineTrials': baseline,
        'candidateTrials': candidate,
        'failureModes': {'baseline': baseline_modes, 'candidate': candidate_modes},
    }
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    with open(a.output, 'w', encoding='utf-8') as handle:
        json.dump(out, handle, indent=2)
    print(json.dumps(out))


if __name__ == '__main__':
    main()
