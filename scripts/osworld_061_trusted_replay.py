"""Revalidate an immutable accepted specialist quorum against an unchanged focal contract."""
import hashlib
import json
import os
import sys
from pathlib import Path

EXPECTED_SOURCE_SHA = '73772dbe40650d2e4561693db00ade48e3134ac1'
EXPECTED_SWARM_SHA256 = 'd2b5f67bf46771c968e4f58437f90d22d7636b4db31ab3b2422eff6bfe9f07f7'
EXPECTED_ROLES = {
    'gimp_gegl_color', 'gtk_accessibility', 'osworld_executor', 'official_evaluator',
    'output_provenance', 'image_quality', 'state_machine', 'recovery_timing',
    'zero_spend_mesh', 'adversarial_qa',
}


def _sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _github_output(name, value):
    target = os.environ.get('GITHUB_OUTPUT')
    if target:
        with open(target, 'a', encoding='utf-8') as handle:
            handle.write(f'{name}={value}\n')


def validate(path):
    path = Path(path)
    current_sha = os.environ.get('GITHUB_SHA', '').strip()
    parity = os.environ.get('TRUSTED_SWARM_FOCAL_PARITY', '') == '1'
    if len(current_sha) != 40:
        raise RuntimeError('CURRENT_SHA_REQUIRED')
    if not parity:
        raise RuntimeError('TRUSTED_SWARM_FOCAL_PARITY_REQUIRED')
    if not path.is_file() or path.stat().st_size <= 0:
        raise RuntimeError('TRUSTED_SWARM_FILE_REQUIRED')
    if _sha256(path) != EXPECTED_SWARM_SHA256:
        raise RuntimeError('TRUSTED_SWARM_HASH_MISMATCH')

    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('candidate_sha') != EXPECTED_SOURCE_SHA:
        raise RuntimeError('TRUSTED_SWARM_SOURCE_SHA_MISMATCH')
    if data.get('status') != 'SWARM_ACCEPTED':
        raise RuntimeError('TRUSTED_SWARM_NOT_ACCEPTED')
    if data.get('robots_total') != 10 or data.get('valid_reviews') != 10:
        raise RuntimeError('TRUSTED_SWARM_QUORUM_MISMATCH')
    if data.get('zero_spend_mode') != 'HARD' or data.get('paid_fallback_used') is not False:
        raise RuntimeError('TRUSTED_SWARM_ZERO_SPEND_MISMATCH')
    if data.get('heavy_local') != 0 or data.get('vetoes') not in ([], None):
        raise RuntimeError('TRUSTED_SWARM_POLICY_MISMATCH')
    reviews = data.get('reviews') or []
    roles = {row.get('role') for row in reviews if isinstance(row, dict)}
    if len(reviews) != 10 or roles != EXPECTED_ROLES:
        raise RuntimeError('TRUSTED_SWARM_ROLE_COVERAGE_MISMATCH')
    for row in reviews:
        verdict = row.get('verdict') or {}
        if verdict.get('verdict') != 'PASS_FIX' or verdict.get('veto') is not False:
            raise RuntimeError('TRUSTED_SWARM_REVIEW_NOT_PASS')
        if verdict.get('root_cause_class') == 'UNKNOWN':
            raise RuntimeError('TRUSTED_SWARM_UNKNOWN_CLASS')

    out = dict(data)
    out['candidate_sha'] = current_sha
    out['revalidated'] = True
    out['revalidation'] = {
        'source_sha': EXPECTED_SOURCE_SHA,
        'source_swarm_sha256': EXPECTED_SWARM_SHA256,
        'focal_contract_parity': True,
        'method': 'immutable_quorum_replay',
    }
    rendered = json.dumps(out, indent=2, sort_keys=True) + '\n'
    Path('osworld-061-specialist-replay.json').write_text(rendered, encoding='utf-8')
    Path('osworld-061-specialist-swarm.json').write_text(rendered, encoding='utf-8')
    _github_output('replay_accepted', '1')
    print(json.dumps({
        'status': out['status'], 'candidate_sha': current_sha,
        'valid_reviews': out['valid_reviews'], 'vetoes': out['vetoes'],
        'revalidated_from': EXPECTED_SOURCE_SHA,
    }, sort_keys=True))
    return out


if __name__ == '__main__':
    validate(sys.argv[1])
