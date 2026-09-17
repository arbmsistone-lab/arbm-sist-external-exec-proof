"""Fail-closed capacity and version preflight for the 061 local fallback runtime."""
import importlib.metadata
import json
import os
import shutil
from pathlib import Path

REQUIRED = {
    'torch': '2.7.1',
    'transformers': '4.52.4',
    'safetensors': '0.8.0',
}
MIN_AVAILABLE_MEMORY_BYTES = 4 * 1024**3
MIN_FREE_DISK_BYTES = 8 * 1024**3


def _github_output(name, value):
    path = os.environ.get('GITHUB_OUTPUT')
    if path:
        with open(path, 'a', encoding='utf-8') as handle:
            handle.write(f'{name}={value}\n')


def _memory_available_bytes():
    meminfo = Path('/proc/meminfo')
    if not meminfo.is_file():
        return 0
    for line in meminfo.read_text(encoding='utf-8', errors='replace').splitlines():
        if line.startswith('MemAvailable:'):
            fields = line.split()
            if len(fields) >= 2 and fields[1].isdigit():
                return int(fields[1]) * 1024
    return 0


def _installed_versions():
    found = {}
    for package in REQUIRED:
        try:
            found[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            found[package] = None
    return found


def evaluate(workspace='.'):
    memory = _memory_available_bytes()
    disk = shutil.disk_usage(workspace).free
    installed = _installed_versions()
    exact = all(installed.get(name) == version for name, version in REQUIRED.items())
    hard_mode = os.environ.get('ZERO_SPEND_MODE') == 'HARD'
    github_hosted = os.environ.get('RUNNER_ENVIRONMENT') == 'github-hosted'
    capacity_ok = memory >= MIN_AVAILABLE_MEMORY_BYTES and disk >= MIN_FREE_DISK_BYTES
    ready = hard_mode and github_hosted and capacity_ok
    return {
        'status': 'HEAVY_RUNTIME_PREFLIGHT_PASS' if ready else 'HEAVY_RUNTIME_PREFLIGHT_BLOCKED',
        'zero_spend_hard': hard_mode,
        'github_hosted': github_hosted,
        'available_memory_bytes': memory,
        'free_disk_bytes': disk,
        'minimum_available_memory_bytes': MIN_AVAILABLE_MEMORY_BYTES,
        'minimum_free_disk_bytes': MIN_FREE_DISK_BYTES,
        'capacity_ok': capacity_ok,
        'required_versions': REQUIRED,
        'installed_versions': installed,
        'exact_runtime_present': exact,
        'install_required': not exact,
    }


def main():
    report = evaluate(os.environ.get('GITHUB_WORKSPACE', '.'))
    Path('osworld-061-heavy-runtime-preflight.json').write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding='utf-8')
    _github_output('install_required', '1' if report['install_required'] else '0')
    _github_output('capacity_ok', '1' if report['capacity_ok'] else '0')
    _github_output('exact_runtime_present', '1' if report['exact_runtime_present'] else '0')
    print(json.dumps(report, sort_keys=True))
    if report['status'] != 'HEAVY_RUNTIME_PREFLIGHT_PASS':
        raise RuntimeError(report['status'])


if __name__ == '__main__':
    main()
