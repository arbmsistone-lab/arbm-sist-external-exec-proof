"""Build and verify a fail-closed evidence bundle for the OSWorld 061 world audit."""
import hashlib
import json
import os
from pathlib import Path

CORE_FILES = (
    'osworld-061-champion-audit.json',
    'osworld-061-specialist-swarm.json',
    'osworld-061-final-3d-audit.json',
    'current-probe-evidence/calibrated/calibrated-probe-result.json',
    'current-probe-evidence/gimp/probe-result.json',
    'current-probe-evidence/gimp/output-absent-before-export.txt',
    'current-probe-evidence/gimp/exported-output.bytes',
    'current-probe-evidence/gimp/exported-output.sha256',
)


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _required_file(path):
    p = Path(path)
    if not p.is_file() or p.stat().st_size <= 0:
        raise RuntimeError(f'EVIDENCE_REQUIRED:{path}')
    return p


def _validate_specialist(path, expected_sha):
    data = _read_json(path)
    if data.get('status') != 'SWARM_ACCEPTED':
        raise RuntimeError(f'SPECIALIST_NOT_ACCEPTED:{path}')
    if data.get('candidate_sha') != expected_sha:
        raise RuntimeError(f'SPECIALIST_SHA_MISMATCH:{path}')
    if data.get('zero_spend_mode') != 'HARD':
        raise RuntimeError(f'SPECIALIST_ZERO_SPEND_MISMATCH:{path}')
    if data.get('paid_fallback_used') is not False or data.get('heavy_local') != 0:
        raise RuntimeError(f'SPECIALIST_POLICY_MISMATCH:{path}')
    if data.get('robots_total') != 10 or data.get('valid_reviews') != 10:
        raise RuntimeError(f'SPECIALIST_QUORUM_MISMATCH:{path}')
    if data.get('vetoes') not in ([], None):
        raise RuntimeError(f'SPECIALIST_VETO_PRESENT:{path}')
    return data


def _hash_tree(root):
    root = Path(root)
    rows = []
    if not root.is_dir():
        return rows
    for path in sorted(p for p in root.rglob('*') if p.is_file()):
        size = path.stat().st_size
        rows.append({'path': path.as_posix(), 'bytes': size, 'sha256': _sha256(path)})
    return rows


def build():
    candidate_sha = os.environ.get('GITHUB_SHA', '').strip()
    if len(candidate_sha) != 40:
        raise RuntimeError('GITHUB_SHA_REQUIRED')
    fast_outcome = os.environ.get('FAST_OUTCOME', '')
    replay_outcome = os.environ.get('REPLAY_OUTCOME', '')
    full_outcome = os.environ.get('FULL_OUTCOME', '')
    audit3d_outcome = os.environ.get('AUDIT3D_OUTCOME', '')
    if audit3d_outcome != 'success':
        raise RuntimeError('AUDIT3D_SUCCESS_REQUIRED')
    if fast_outcome != 'success' and replay_outcome != 'success' and full_outcome != 'success':
        raise RuntimeError('ACCEPTED_SPECIALIST_LANE_REQUIRED')

    for path in CORE_FILES:
        _required_file(path)

    champion = _read_json('osworld-061-champion-audit.json')
    audit3d = _read_json('osworld-061-final-3d-audit.json')
    if champion.get('status') != 'PASS':
        raise RuntimeError('CHAMPION_AUDIT_PASS_REQUIRED')
    if audit3d.get('status') != 'PASS' or audit3d.get('passed') != 60:
        raise RuntimeError('FINAL_3D_AUDIT_PASS_REQUIRED')

    specialist = _validate_specialist('osworld-061-specialist-swarm.json', candidate_sha)
    fast = None
    replay = None
    if fast_outcome == 'success':
        _required_file('osworld-061-specialist-fast-path.json')
        fast = _validate_specialist('osworld-061-specialist-fast-path.json', candidate_sha)
    if replay_outcome == 'success':
        _required_file('osworld-061-specialist-replay.json')
        replay = _validate_specialist('osworld-061-specialist-replay.json', candidate_sha)
        validation = replay.get('revalidation') or {}
        if replay.get('revalidated') is not True or validation.get('focal_contract_parity') is not True:
            raise RuntimeError('SPECIALIST_REPLAY_PARITY_REQUIRED')
        if validation.get('method') != 'immutable_quorum_replay':
            raise RuntimeError('SPECIALIST_REPLAY_METHOD_MISMATCH')
    if full_outcome == 'success':
        _required_file('osworld-061-heavy-runtime-preflight.json')
        preflight = _read_json('osworld-061-heavy-runtime-preflight.json')
        if preflight.get('status') != 'HEAVY_RUNTIME_PREFLIGHT_PASS':
            raise RuntimeError('HEAVY_RUNTIME_PREFLIGHT_PASS_REQUIRED')
    else:
        preflight = None

    probe_files = _hash_tree('current-probe-evidence')
    if not probe_files:
        raise RuntimeError('CURRENT_PROBE_EVIDENCE_TREE_REQUIRED')
    core_hashes = []
    for path in CORE_FILES:
        p = Path(path)
        core_hashes.append({'path': path, 'bytes': p.stat().st_size, 'sha256': _sha256(p)})
    for optional in ('osworld-061-specialist-fast-path.json', 'osworld-061-specialist-replay.json',
                     'osworld-061-heavy-runtime-preflight.json'):
        p = Path(optional)
        if p.is_file() and p.stat().st_size > 0:
            core_hashes.append({'path': optional, 'bytes': p.stat().st_size, 'sha256': _sha256(p)})

    out = {
        'status': 'EVIDENCE_BUNDLE_VERIFIED',
        'candidate_sha': candidate_sha,
        'approved_focal_sha': os.environ.get('APPROVED_FOCAL_SHA'),
        'approved_focal_run_id': os.environ.get('APPROVED_FOCAL_RUN_ID'),
        'diagnostic_probe_sha': os.environ.get('DIAGNOSTIC_PROBE_SHA'),
        'diagnostic_probe_run_id': os.environ.get('DIAGNOSTIC_PROBE_RUN_ID'),
        'lane_outcomes': {
            'fast': fast_outcome, 'replay': replay_outcome,
            'full': full_outcome, 'audit3d': audit3d_outcome,
        },
        'zero_spend_mode': 'HARD', 'paid_fallback_used': False, 'heavy_local': 0,
        'champion_status': champion.get('status'),
        'specialist_status': specialist.get('status'),
        'fast_status': fast.get('status') if fast else None,
        'replay_status': replay.get('status') if replay else None,
        'preflight_status': preflight.get('status') if preflight else None,
        'final_3d_status': audit3d.get('status'),
        'core_files': sorted(core_hashes, key=lambda row: row['path']),
        'probe_tree': probe_files,
    }
    rendered = json.dumps(out, indent=2, sort_keys=True) + '\n'
    Path('osworld-061-evidence-bundle.json').write_text(rendered, encoding='utf-8')
    bundle_sha = hashlib.sha256(rendered.encode()).hexdigest()
    Path('osworld-061-evidence-bundle.sha256').write_text(
        f'{bundle_sha}  osworld-061-evidence-bundle.json\n', encoding='utf-8')
    print(json.dumps({'status': out['status'], 'candidate_sha': candidate_sha,
                      'core_files': len(core_hashes), 'probe_files': len(probe_files),
                      'bundle_sha256': bundle_sha}, sort_keys=True))
    return out


if __name__ == '__main__':
    build()
