#!/usr/bin/env python3
"""Add only an explicit observation hook to a pinned upstream runtime module."""
import argparse
import subprocess
from pathlib import Path

EXPECTED_UPSTREAM = 'd578d2d4e0dc82b43e270fdaa7fa89d9708cd154'
EXPECTED_BLOB = '005edd53421f5c1bf7512f3ff377ee7d9fe209aa'
HOOK = '''

# ARBM_091_READ_ONLY_OBSERVER_V1: runtime instrumentation, not an evaluator patch.
if os.environ.get("ARBM_WPS_OBSERVER") == "1":
    from arbm091.wps_observer import install as _arbm091_install_observer
    _arbm091_install_observer(DesktopEnv)
'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('upstream', type=Path)
    args = parser.parse_args()
    root = args.upstream.resolve()
    sha = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    if sha != EXPECTED_UPSTREAM:
        raise SystemExit('UPSTREAM_SHA_MISMATCH')
    path = root / 'desktop_env/desktop_env.py'
    raw = path.read_bytes()
    blob = subprocess.check_output(['git', '-C', str(root), 'hash-object', '--stdin'], input=raw).decode().strip()
    if blob != EXPECTED_BLOB:
        raise SystemExit('UPSTREAM_RUNTIME_BLOB_CHANGED')
    text = raw.decode()
    if 'class DesktopEnv' not in text or 'import os' not in text:
        raise SystemExit('UPSTREAM_RUNTIME_CONTRACT_CHANGED')
    path.write_text(text + HOOK)
    print('ARBM_091_READ_ONLY_OBSERVER_INSTALLED')


if __name__ == '__main__':
    main()
