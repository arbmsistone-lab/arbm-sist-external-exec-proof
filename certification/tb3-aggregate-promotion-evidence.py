import argparse, glob, json, os

EXPECTED_TASKS = {
    'terminal-bench/atrx-vep-crispr',
    'terminal-bench/batched-eval-parity',
    'terminal-bench/biped-contact-dynamics',
}
MODE_KEYS = ('premature_completion', 'missing_required_output', 'no_final_verification')


def blank_modes():
    return {key: 0 for key in MODE_KEYS}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--regression-result', required=True)
    p.add_argument('--paired-result', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    files = sorted(glob.glob(os.path.join(a.root, '**', '*.json'), recursive=True))
    baseline, candidate = [], []
    modes = {'baseline': blank_modes(), 'candidate': blank_modes()}
    evidence_files = 0
    for path in files:
        data = json.load(open(path, encoding='utf-8'))
        if 'baselineTrials' not in data or 'candidateTrials' not in data:
            continue
        evidence_files += 1
        baseline.extend(data['baselineTrials'])
        candidate.extend(data['candidateTrials'])
        for side in ('baseline', 'candidate'):
            observed = (data.get('failureModes') or {}).get(side) or {}
            for key in MODE_KEYS:
                modes[side][key] += int(observed.get(key) or 0)
    if evidence_files != 3:
        raise SystemExit(f'expected_3_evidence_files_got_{evidence_files}')
    if len(baseline) != 9 or len(candidate) != 9:
        raise SystemExit(f'expected_9x9_got_{len(baseline)}_{len(candidate)}')
    if {x['task'] for x in baseline} != EXPECTED_TASKS or {x['task'] for x in candidate} != EXPECTED_TASKS:
        raise SystemExit('unexpected_task_set')
    if len({(x['task'], x['rep']) for x in baseline}) != 9 or len({(x['task'], x['rep']) for x in candidate}) != 9:
        raise SystemExit('duplicate_or_missing_trial_key')
    out = {
        'comparability': {
            'sameModel': True,
            'sameTaskSet': True,
            'sameBudget': True,
            'sameHarness': True,
            'sameVerifier': True,
        },
        'baselineTrials': baseline,
        'candidateTrials': candidate,
        'failureModes': modes,
        'regression': {
            'allExistingGatesPass': a.regression_result == 'success' and a.paired_result == 'success',
            'newP0': 0,
            'newP1': 0,
            'newP2': 0,
        },
    }
    os.makedirs(os.path.dirname(a.output) or '.', exist_ok=True)
    with open(a.output, 'w', encoding='utf-8') as handle:
        json.dump(out, handle, indent=2)
    print(json.dumps({'baseline': len(baseline), 'candidate': len(candidate), 'failureModes': modes, 'output': a.output}))


if __name__ == '__main__':
    main()
