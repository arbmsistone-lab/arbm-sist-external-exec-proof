"""Write a compact forensic receipt for one bounded 061 audit lane."""
import json
import os
import sys
from pathlib import Path

ALLOWED = {'fast', 'full'}


def build(lane, rc, started_epoch, finished_epoch):
    if lane not in ALLOWED:
        raise ValueError('LANE_NOT_ALLOWED')
    rc = int(rc)
    started = int(started_epoch)
    finished = int(finished_epoch)
    if started <= 0 or finished < started:
        raise ValueError('LANE_TIME_INVALID')
    out = {
        'lane': lane,
        'candidate_sha': os.environ.get('GITHUB_SHA'),
        'exit_code': rc,
        'timed_out': rc == 124,
        'success': rc == 0,
        'started_epoch': started,
        'finished_epoch': finished,
        'elapsed_seconds': finished - started,
        'zero_spend_mode': os.environ.get('ZERO_SPEND_MODE'),
        'paid_fallback_used': False,
        'heavy_local': 0,
    }
    path = Path(f'osworld-061-{lane}-lane-receipt.json')
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(out, sort_keys=True))
    return out


if __name__ == '__main__':
    if len(sys.argv) != 5:
        raise SystemExit('usage: lane_receipt.py <fast|full> <rc> <started_epoch> <finished_epoch>')
    build(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
