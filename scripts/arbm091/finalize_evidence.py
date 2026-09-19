"""Completion receipt outside the sealed directory; no score is changed."""
import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    path = args.root.with_name(args.root.name + '.complete.json')
    if path.exists():
        raise SystemExit('COMPLETION_RECEIPT_ALREADY_EXISTS')
    record = {'candidate_sha': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
              'run_attempt': os.environ['GITHUB_RUN_ATTEMPT']}
    temporary = path.with_suffix('.temporary')
    temporary.write_text(json.dumps(record, sort_keys=True) + '\n')
    temporary.replace(path)


if __name__ == '__main__':
    main()
