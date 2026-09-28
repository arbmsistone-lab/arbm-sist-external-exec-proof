#!/usr/bin/env python3
"""Patch the pinned OSWorld runner without touching official evaluators.

The upstream classic runner writes obs["screenshot"] directly. Some applications
can transiently return a None screenshot after a valid GUI step, which aborts the
episode before env.evaluate() and prevents result.txt from being emitted.
This patch only reacquires observation bytes with a bounded retry and fails closed
if bytes remain unavailable.
"""
from __future__ import annotations
import argparse
from pathlib import Path

MARKER = "ARBM_OSWORLD_SCREENSHOT_REACQUIRE_V1"
WRITE_EXPR = "_f.write(obs['screenshot'])"

HELPER = r'''
# ARBM_OSWORLD_SCREENSHOT_REACQUIRE_V1
def _arbm_require_screenshot(env, obs, attempts=4):
    current = obs if isinstance(obs, dict) else {}
    for index in range(max(1, int(attempts))):
        value = current.get("screenshot")
        if isinstance(value, (bytes, bytearray, memoryview)) and len(value):
            return bytes(value)
        time.sleep(0.25 * (index + 1))
        current = env._get_obs()
        if not isinstance(current, dict):
            current = {}
    raise RuntimeError("OSWORLD_SCREENSHOT_REACQUIRE_FAILED")
'''


def patch_text(source: str) -> str:
    if MARKER in source:
        return source
    anchor = 'logger = logging.getLogger("desktopenv.experiment")\n'
    if anchor not in source:
        raise RuntimeError("OSWORLD_RUNNER_PATCH_ANCHOR_MISSING")
    count = source.count(WRITE_EXPR)
    if count < 1:
        raise RuntimeError("OSWORLD_SCREENSHOT_WRITE_PATTERN_MISSING")
    source = source.replace(anchor, anchor + "\n" + HELPER + "\n", 1)
    source = source.replace(WRITE_EXPR, "_f.write(_arbm_require_screenshot(env, obs))")
    if WRITE_EXPR in source or MARKER not in source:
        raise RuntimeError("OSWORLD_RUNNER_PATCH_INCOMPLETE")
    return source


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    original = args.path.read_text(encoding="utf-8")
    patched = patch_text(original)
    args.path.write_text(patched, encoding="utf-8")
    print(f"OSWORLD_RUNNER_SCREENSHOT_PATCH=PASS replacements={original.count(WRITE_EXPR)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
