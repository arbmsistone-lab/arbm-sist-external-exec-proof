"""Reproduce ten evidence audits of one immutable FREE candidate; no inference."""
import argparse
import hashlib
import io
import json
import re
import subprocess
import tarfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from g3_free_control import journal_report

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'certification/g3-free-evidence-20260911'
BASE = '47aee38f0873cdd3964aea5ef03caf6c982483be'
CODE = (
    'certification/g3-openrouter-free-adapter.py', 'certification/g3_free_control.py',
    'certification/g3_free_route_admission.py', 'certification/g3_free_closeout_audit.py',
    'tests/test_g3_free_agent.py', 'tests/test_g3_free_workflow.py',
    'tests/test_g3_free_route_admission.py',
    '.github/workflows/osworld-g3-free-smoke-v1.yml',
    '.github/workflows/g3-free-account-readonly.yml',
)
SECRET = re.compile(rb'(?:sk-or-v1-[A-Za-z0-9]{30,}|gsk_[A-Za-z0-9]{30,}|'
                    rb'gh[pousr]_[A-Za-z0-9]{30,}|AIza[A-Za-z0-9_-]{30,}|'
                    rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def audit(candidate, number):
    hashes = {}
    checks = {}
    for name in CODE:
        data = (ROOT / name).read_bytes()
        committed = git('show', candidate + ':' + name)
        # Git-enforced LF files compare semantically on Windows working trees.
        checks[name] = data.replace(b'\r\n', b'\n') == committed.replace(b'\r\n', b'\n')
        hashes[name] = sha(committed)
    changes = git('diff', '--name-only', BASE, candidate).decode().splitlines()
    unexpected = [p for p in changes if p not in CODE and
                  not p.startswith('certification/g3-free-evidence-20260911/') and
                  p not in ('.gitattributes', 'certification/g3-free-quota-lock.json')]
    checks['paid_production_and_vendor_unchanged'] = not unexpected
    checks['branch'] = git('branch', '--show-current').decode().strip() == 'g3-free-cert-lane-20260910'
    checks['candidate_is_exact_commit'] = git('rev-parse', candidate + '^{commit}').decode().strip() == candidate
    workflow = (ROOT / CODE[-2]).read_text()
    checks['official_pins'] = all(value in workflow for value in (
        'd578d2d4e0dc82b43e270fdaa7fa89d9708cd154', 'v2026.08.08',
        'eb737ae70b49849e24af407de6a518439a23de05a8497096a948334ce0a909aa',
        '8213366932c553e5fe758d0f2c8c8b81ffc3be8c',
        '0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9'))
    checks['remote_zero_spend_contract'] = "HEAVY_LOCAL: '0'" in workflow and "ZERO_SPEND: 'true'" in workflow
    test_text = (PACK / 'local-tests-final.txt').read_text(encoding='utf-8-sig')
    checks['local_tests_34_pass'] = 'Ran 34 tests' in test_text and '\nOK' in test_text
    matches = []
    for name in CODE:
        if SECRET.search((ROOT / name).read_bytes()):
            matches.append(name)
    journals = {}
    archives = {}
    trajectory = {}
    for directory in sorted((PACK / 'runs').iterdir()):
        for item in read(directory / 'artifact-index.json'):
            data = (directory / 'artifact.zip').read_bytes()
            digest_ok = 'sha256:' + sha(data) == item['digest']
            archives[directory.name] = digest_ok
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for name in archive.namelist():
                    if name.endswith(('.json', '.jsonl', '.txt')) and SECRET.search(archive.read(name)):
                        matches.append(directory.name + '/' + name)
                    if name.endswith('official-trajectory.tar.gz'):
                        with tarfile.open(fileobj=io.BytesIO(archive.read(name)), mode='r:gz') as tar:
                            members = tar.getnames()
                            trajectory = {'run': directory.name,
                                          'screenshots': sum(p.endswith('.png') for p in members),
                                          'official_result_present': any(p.endswith('/result.txt') for p in members)}
        for path in directory.glob('g3-free-*.jsonl'):
            journals[directory.name + '/' + path.name] = journal_report(path)
    checks['artifact_digests_verified'] = len(archives) == 3 and all(archives.values())
    checks['journals_reconciled'] = bool(journals) and all(r['accounting_complete'] for r in journals.values())
    checks['no_matching_secrets_in_code_or_original_text_artifacts'] = not matches
    integrity = read(PACK / 'runs/34598530042/free-integrity.json')
    checks['official_17_input_files_unchanged_in_live_run'] = integrity == {'official_inputs_unchanged': True, 'files': 17}
    blockers = [
        'OPENROUTER_DAILY_QUOTA_EXHAUSTED_UNTIL_2026-09-12T00:00:00Z',
        'GROQ_ACCOUNT_AUTHENTICATION_AND_FREE_PLAN_PROOF_MISSING',
        'INDEPENDENT_ROUTE_CREDENTIAL_AND_LIVE_PROBE_MISSING',
        'LATEST_AGENT_GROUNDING_CORRECTION_HAS_NO_OFFICIAL_RETEST',
        'OFFICIAL_EVALUATOR_RESULT_MISSING', 'STABILITY_NOT_PROVEN',
        'FULL_108_TASK_SUITE_NOT_RUN', 'COMPARABLE_TOP3_NOT_PROVEN',
        'RUNTIME_REGRESSION_GATE_OPEN',
    ]
    return {'round': number, 'candidate_sha': candidate,
            'observed_at_utc': datetime.now(timezone.utc).isoformat(),
            'checks': checks, 'all_available_checks_pass': all(checks.values()),
            'code_hashes': hashes, 'unexpected_changed_paths': unexpected,
            'secret_match_paths_only': matches, 'journals': journals,
            'artifact_digests': archives, 'trajectory': trajectory,
            'official_score': None, 'closure_state': 'BLOCKED', 'blockers': blockers}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', required=True)
    args = parser.parse_args()
    rounds = [audit(args.candidate, number) for number in range(1, 11)]
    report = {'candidate_sha': args.candidate,
              'scope': 'Ten repeated code/evidence audits; not ten benchmarks or stability runs',
              'classification': 'EXTERNAL_BLOCKED', 'green_proven': False,
              'top3_proven': False, 'rounds': rounds}
    (PACK / 'closure-audit-10x.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'candidate': args.candidate, 'rounds': len(rounds),
                      'available_checks_pass': all(r['all_available_checks_pass'] for r in rounds),
                      'closure': 'BLOCKED', 'inference_calls': 0, 'vms_prepared': 0}))
    return 0 if all(r['all_available_checks_pass'] for r in rounds) else 1


if __name__ == '__main__':
    raise SystemExit(main())
