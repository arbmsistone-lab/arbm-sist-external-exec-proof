"""Observe Docker launch failures without changing evaluator commands or results."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time

ORIGINAL_RUN = subprocess.run
OUT = Path(os.environ['GITHUB_WORKSPACE']) / 'p9-eval' / 'docker-diagnostics'


def record(name, command):
    result = ORIGINAL_RUN(command, capture_output=True, text=True, timeout=45)
    payload = {'command': command, 'returncode': result.returncode,
               'stdout': result.stdout, 'stderr': result.stderr}
    (OUT / (name + '.json')).write_text(json.dumps(payload, indent=2))
    return result


def diagnose(command, result):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'original-run.json').write_text(json.dumps({
        'command': command, 'returncode': result.returncode,
        'stdout': result.stdout, 'stderr': result.stderr}, indent=2))
    print('Docker launch stderr: ' + str(result.stderr), file=sys.stderr, flush=True)
    image = next(x for x in command if x.startswith('sha256:'))
    record('image-inspect', ['docker', 'image', 'inspect', image, '--format',
        '{{json .Id}} {{json .Config.Entrypoint}} {{json .Config.Cmd}} '
        '{{json .Config.User}} {{json .Config.WorkingDir}} '
        '{{json .Architecture}} {{json .Os}} {{json .Config.Volumes}}'])
    record('daemon', ['docker', 'info', '--format',
        '{{json .NCPU}} {{json .SecurityOptions}} {{json .InitBinary}} '
        '{{json .Driver}} {{json .CgroupVersion}} {{json .OperatingSystem}}'])
    record('version', ['docker', 'version'])
    record('host', ['bash', '-c', 'nproc; ulimit -a; df -h; ls -l /dev/null; command -v docker-init || true'])
    name = command[command.index('--name') + 1]
    record('failed-container', ['docker', 'inspect', name, '--format',
        '{{json .State}} {{json .Mounts}} {{json .HostConfig}}'])
    # One causal control: same image/options/mount/init/cmd, only CPU capacity changes.
    capacity = record('cpu-capacity', ['docker', 'info', '--format', '{{.NCPU}}'])
    cpus = int(capacity.stdout.strip())
    control = list(command)
    control[control.index('--cpus') + 1] = str(cpus)
    probe_name = 'p9-cpu-control-' + str(os.getpid())
    control[control.index('--name') + 1] = probe_name
    try:
        launched = record('cpu-only-control', control)
        if launched.returncode == 0:
            record('control-inspect', ['docker', 'inspect', probe_name, '--format',
                '{{json .State}} {{json .Mounts}} {{json .HostConfig}}'])
            record('control-runtime', ['docker', 'exec', probe_name, 'sh', '-c',
                'id; pwd; command -v tail; ls -l /dev/null; test -c /dev/null && '
                'test -r /dev/null && test -w /dev/null; ulimit -a; '
                'test -d /output; ls -ld /output; cat /proc/1/comm'])
    finally:
        record('control-cleanup', ['docker', 'rm', '-f', probe_name])


def observed_run(command, *args, **kwargs):
    target = isinstance(command, (list, tuple)) and list(command[:2]) == ['docker', 'run'] and '--cpus' in command
    if not target:
        return ORIGINAL_RUN(command, *args, **kwargs)
    try:
        result = ORIGINAL_RUN(command, *args, **kwargs)
    except subprocess.CalledProcessError as error:
        try:
            diagnose(command, error)
        except Exception as diagnostic_error:
            print('Diagnostic collection failed: ' + str(diagnostic_error), file=sys.stderr)
        raise
    if result.returncode:
        diagnose(command, result)
    return result


if __name__ == '__main__':
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('ZERO_SPEND_MODE') != 'HARD':
        raise SystemExit('WAITING_FREE_CAPACITY: cloud-only observer')
    subprocess.run = observed_run
    runpy.run_module('harness.e2e.evaluator', run_name='__main__')
