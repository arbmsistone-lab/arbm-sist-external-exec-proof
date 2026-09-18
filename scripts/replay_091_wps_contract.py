"""Replay a genuine captured WPS observation, never a MailHub substitute."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

from osworld_wps_focus import APP, install, norm, observed_app, validate_action


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('ZERO_SPEND_MODE') != 'HARD' or os.environ.get('ARBM_STRICT_WPS') != '1':
        raise SystemExit('STRICT_WPS_ZERO_SPEND_REQUIRED')
    import osworld_free_mesh_shim as shim
    import osworld_local_vlm as local
    install(shim, local)
    selected = None
    inventory = []
    for path in sorted(args.root.rglob('step_*.json')):
        data = json.loads(path.read_text())
        body = data.get('request', {})
        obs = str(body.get('observation') or '')
        try:
            app = observed_app(obs, allow_canonical_prefix=True)
        except ValueError:
            app = 'unproven'
        inventory.append({'file': str(path.relative_to(args.root)), 'app': app})
        if app == APP and norm(body.get('active_application')) == APP and body.get('screenshot_data_url'):
            selected = (path, body)
            break
    if selected is None:
        print(json.dumps({'status': 'WPS_CAPTURE_NOT_FOUND', 'inventory': inventory}))
        raise SystemExit('WPS_CAPTURE_NOT_FOUND')
    path, body = selected
    values = []
    for _ in range(2):
        result, attempts = local.LOCAL_VLM_ROUTE.call(body, budget=105)
        if result is None:
            print(json.dumps({'status': 'WPS_REPLAY_BLOCKED', 'attempts': attempts}))
            raise SystemExit('WPS_REPLAY_BLOCKED')
        action = result['action']
        validate_action(action, body['observation'], canonical=True)
        if not any(a.get('status') == 200 and a.get('selector_mode') == 'single_forward_logits'
                   and a.get('zero_spend_confirmed') is True for a in attempts):
            raise SystemExit('WPS_SELECTOR_ROUTE_UNPROVEN')
        values.append({'action': action, 'attempts': attempts})
    if values[0]['action'] != values[1]['action']:
        raise SystemExit('WPS_REPLAY_NONDETERMINISTIC')
    report = {'status': 'WPS_ONLY_LOCAL_CONTRACT_PASS', 'official_score_claimed': False,
              'candidate_sha': os.environ.get('GITHUB_SHA'), 'source_run': '35337481350',
              'source_artifact': '10544636575', 'observation': str(path.relative_to(args.root)),
              'observation_file_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'observed_app': APP, 'model': local.MODEL, 'model_revision': local.MODEL_REVISION,
              'zero_spend_mode': 'HARD', 'replays': values}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
