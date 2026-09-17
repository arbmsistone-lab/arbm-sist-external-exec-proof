"""Build and verify a fail-closed evidence bundle for the OSWorld 061 world audit."""
import hashlib
import json
import os
from pathlib import Path

EXPORTED_OUTPUT = 'current-probe-evidence/gimp/IMG_7318_edited.jpg'
CORE_FILES = (
    'osworld-061-champion-audit.json',
    'osworld-061-specialist-swarm.json',
    'osworld-061-final-3d-audit.json',
    'current-probe-evidence/calibrated/calibrated-probe-result.json',
    'current-probe-evidence/gimp/probe-result.json',
    'current-probe-evidence/gimp/output-absent-before-export.txt',
    'current-probe-evidence/gimp/exported-output.bytes',
    'current-probe-evidence/gimp/exported-output.sha256',
    EXPORTED_OUTPUT,
)
EXPECTED_ROLES = {
    'gimp_gegl_color', 'gtk_accessibility', 'osworld_executor', 'official_evaluator',
    'output_provenance', 'image_quality', 'state_machine', 'recovery_timing',
    'zero_spend_mesh', 'adversarial_qa',
}


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
    reviews = data.get('reviews') or []
    roles = {row.get('role') for row in reviews if isinstance(row, dict)}
    if len(reviews) != 10 or roles != EXPECTED_ROLES:
        raise RuntimeError(f'SPECIALIST_ROLE_COVERAGE_MISMATCH:{path}')
    for row in reviews:
        verdict = row.get('verdict') or {}
        if verdict.get('verdict') != 'PASS_FIX' or verdict.get('veto') is not False:
            raise RuntimeError(f'SPECIALIST_REVIEW_NOT_PASS:{path}')
        if verdict.get('root_cause_class') == 'UNKNOWN':
            raise RuntimeError(f'SPECIALIST_UNKNOWN_CLASS:{path}')
    return data


def _validate_lane_receipt(path, lane, expected_sha, expected_success):
    data = _read_json(_required_file(path))
    if data.get('lane') != lane or data.get('candidate_sha') != expected_sha:
        raise RuntimeError(f'LANE_RECEIPT_IDENTITY_MISMATCH:{path}')
    if data.get('zero_spend_mode') != 'HARD' or data.get('paid_fallback_used') is not False:
        raise RuntimeError(f'LANE_RECEIPT_ZERO_SPEND_MISMATCH:{path}')
    if data.get('heavy_local') != 0 or data.get('timed_out') not in (True, False):
        raise RuntimeError(f'LANE_RECEIPT_POLICY_MISMATCH:{path}')
    if data.get('success') is not expected_success:
        raise RuntimeError(f'LANE_RECEIPT_OUTCOME_MISMATCH:{path}')
    rc = data.get('exit_code')
    if not isinstance(rc, int) or (expected_success and rc != 0) or (not expected_success and rc == 0):
        raise RuntimeError(f'LANE_RECEIPT_EXIT_CODE_MISMATCH:{path}')
    started = data.get('started_epoch')
    finished = data.get('finished_epoch')
    elapsed = data.get('elapsed_seconds')
    if not all(isinstance(v, int) for v in (started, finished, elapsed)):
        raise RuntimeError(f'LANE_RECEIPT_TIME_MISSING:{path}')
    if started <= 0 or finished < started or elapsed != finished - started:
        raise RuntimeError(f'LANE_RECEIPT_TIME_INVALID:{path}')
    return data


def _validate_export_provenance():
    payload = _required_file(EXPORTED_OUTPUT)
    bytes_file = _required_file('current-probe-evidence/gimp/exported-output.bytes')
    digest_file = _required_file('current-probe-evidence/gimp/exported-output.sha256')
    try:
        declared_bytes = int(bytes_file.read_text(encoding='utf-8').strip())
    except ValueError as exc:
        raise RuntimeError('EXPORTED_OUTPUT_BYTES_FORMAT_INVALID') from exc
    if declared_bytes != payload.stat().st_size or declared_bytes <= 1024:
        raise RuntimeError('EXPORTED_OUTPUT_BYTES_MISMATCH')
    expected = digest_file.read_text(encoding='utf-8').strip().split()[0]
    if len(expected) != 64 or any(c not in '0123456789abcdefABCDEF' for c in expected):
        raise RuntimeError('EXPORTED_OUTPUT_HASH_FORMAT_INVALID')
    actual = _sha256(payload)
    if actual.lower() != expected.lower():
        raise RuntimeError('EXPORTED_OUTPUT_HASH_MISMATCH')
    probe = _read_json('current-probe-evidence/gimp/probe-result.json')
    if probe.get('status') != 'EXPORT_PROVEN':
        raise RuntimeError('GIMP_EXPORT_PROVEN_REQUIRED')
    if probe.get('output') != Path(EXPORTED_OUTPUT).name:
        raise RuntimeError('GIMP_EXPORT_NAME_MISMATCH')
    if probe.get('output_bytes') != declared_bytes or probe.get('output_sha256') != actual:
        raise RuntimeError('GIMP_EXPORT_RECEIPT_MISMATCH')
    if probe.get('zero_spend_mode') != 'HARD' or probe.get('heavy_local') != 0:
        raise RuntimeError('GIMP_EXPORT_POLICY_MISMATCH')
    return {'bytes': declared_bytes, 'sha256': actual}


def _hash_tree(root):
    root = Path(root)
    rows = []
    if not root.is_dir():
        return rows
    for path in sorted(p for p in root.rglob('*') if p.is_file()):
        size = path.stat().st_size
        if size <= 0:
            raise RuntimeError(f'EVIDENCE_REQUIRED:{path.as_posix()}')
        rows.append({'path': path.as_posix(), 'bytes': size, 'sha256': _sha256(path)})
    return rows


def build():
    candidate_sha = os.environ.get('GITHUB_SHA', '').strip()
    if len(candidate_sha) != 40:
        raise RuntimeError('GITHUB_SHA_REQUIRED')
    if os.environ.get('ZERO_SPEND_MODE') != 'HARD':
        raise RuntimeError('ZERO_SPEND_HARD_REQUIRED')
    if os.environ.get('APPROVED_FOCAL_EVIDENCE_BOUND') != '1':
        raise RuntimeError('APPROVED_FOCAL_EVIDENCE_BIND_REQUIRED')
    if os.environ.get('DIAGNOSTIC_EXECUTION_PARITY') != '1':
        raise RuntimeError('DIAGNOSTIC_EXECUTION_PARITY_REQUIRED')
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
    export_provenance = _validate_export_provenance()

    champion = _read_json('osworld-061-champion-audit.json')
    audit3d = _read_json('osworld-061-final-3d-audit.json')
    if champion.get('status') != 'PASS':
        raise RuntimeError('CHAMPION_AUDIT_PASS_REQUIRED')
    if audit3d.get('status') != 'PASS' or audit3d.get('passed') != 60:
        raise RuntimeError('FINAL_3D_AUDIT_PASS_REQUIRED')

    specialist = _validate_specialist('osworld-061-specialist-swarm.json', candidate_sha)
    fast = None
    replay = None
    fast_receipt = _validate_lane_receipt(
        'osworld-061-fast-lane-receipt.json', 'fast', candidate_sha, fast_outcome == 'success')
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
        full_receipt = _validate_lane_receipt(
            'osworld-061-full-lane-receipt.json', 'full', candidate_sha, True)
        _required_file('osworld-061-heavy-runtime-preflight.json')
        preflight = _read_json('osworld-061-heavy-runtime-preflight.json')
        if preflight.get('status') != 'HEAVY_RUNTIME_PREFLIGHT_PASS':
            raise RuntimeError('HEAVY_RUNTIME_PREFLIGHT_PASS_REQUIRED')
    else:
        full_receipt = None
        preflight = None

    probe_files = _hash_tree('current-probe-evidence')
    if not probe_files:
        raise RuntimeError('CURRENT_PROBE_EVIDENCE_TREE_REQUIRED')
    core_hashes = []
    for path in CORE_FILES:
        p = Path(path)
        core_hashes.append({'path': path, 'bytes': p.stat().st_size, 'sha256': _sha256(p)})
    for optional in ('osworld-061-fast-lane-receipt.json', 'osworld-061-full-lane-receipt.json',
                     'osworld-061-specialist-fast-path.json', 'osworld-061-specialist-replay.json',
                     'osworld-061-heavy-runtime-preflight.json'):
        p = Path(optional)
        if p.is_file() and p.stat().st_size > 0:
            core_hashes.append({'path': optional, 'bytes': p.stat().st_size, 'sha256': _sha256(p)})

    out = {
        'status': 'EVIDENCE_BUNDLE_VERIFIED',
        'candidate_sha': candidate_sha,
        'approved_focal_sha': os.environ.get('APPROVED_FOCAL_SHA'),
        'approved_focal_run_id': os.environ.get('APPROVED_FOCAL_RUN_ID'),
        'approved_focal_evidence_bound': True,
        'diagnostic_probe_sha': os.environ.get('DIAGNOSTIC_PROBE_SHA'),
        'diagnostic_probe_run_id': os.environ.get('DIAGNOSTIC_PROBE_RUN_ID'),
        'diagnostic_execution_parity': True,
        'exported_output_bytes': export_provenance['bytes'],
        'exported_output_sha256': export_provenance['sha256'],
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
        'fast_receipt_success': fast_receipt.get('success'),
        'full_receipt_success': full_receipt.get('success') if full_receipt else None,
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
