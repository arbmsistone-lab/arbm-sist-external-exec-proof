#!/usr/bin/env python3
"""Replay the exact 091 observation through the currently promoted local desktop route.

The promoted desktop path is selector-based (single-forward logits), not legacy
free-form generation. Reproducibility therefore means the same pinned model,
input and policy select the same safe canonical action twice. Raw prose hashes
from the legacy generator are intentionally not used as certification evidence.
"""
import argparse
import json
import os
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from osworld_local_vlm import LocalVLMRoute, MODEL, MODEL_REVISION


def canonical_action_key(action):
    if not isinstance(action,dict):
        return None
    target=action.get('target') if isinstance(action.get('target'),dict) else {}
    return {
        'action':str(action.get('action') or ''),
        'command':str(action.get('command') or ''),
        'target_source':str(target.get('source') or ''),
        'target_role':str(target.get('role') or ''),
        'target_label':str(target.get('label') or ''),
        'target_proof_sha256':str(target.get('proof_sha256') or ''),
    }


def run_once(body):
    route=LocalVLMRoute()
    result,attempts=route.call(body,budget=105)
    record={
        'model':MODEL,
        'model_revision':MODEL_REVISION,
        'result':result,
        'attempts':attempts,
    }
    if result is None:
        raise SystemExit('LOCAL_ROUTE_NO_ACTION:'+json.dumps(record,sort_keys=True))
    action=result.get('action')
    key=canonical_action_key(action)
    if not key or key['action']!='exec' or not key['command']:
        raise SystemExit('LOCAL_ROUTE_ACTION_INVALID:'+json.dumps(record,sort_keys=True))
    final=attempts[-1] if attempts else {}
    if final.get('status')!=200 or final.get('zero_spend_confirmed') is not True:
        raise SystemExit('LOCAL_ROUTE_ZERO_SPEND_UNPROVEN:'+json.dumps(record,sort_keys=True))
    if final.get('selector_mode')!='single_forward_logits':
        raise SystemExit('LOCAL_ROUTE_SELECTOR_MODE_UNPROVEN:'+json.dumps(record,sort_keys=True))
    target=action.get('target') if isinstance(action.get('target'),dict) else {}
    if 'pyautogui.click' in key['command'] or 'pyautogui.doubleClick' in key['command'] or 'pyautogui.rightClick' in key['command']:
        if target.get('source')!='accessibility-canonical':
            raise SystemExit('LOCAL_ROUTE_POINTER_NOT_CANONICAL:'+json.dumps(record,sort_keys=True))
        if not target.get('proof_sha256'):
            raise SystemExit('LOCAL_ROUTE_POINTER_PROOF_MISSING:'+json.dumps(record,sort_keys=True))
    return key,record


def main():
    p=argparse.ArgumentParser()
    p.add_argument('observation_json')
    args=p.parse_args()
    if os.environ.get('ZERO_SPEND_MODE')!='HARD':
        raise SystemExit('ZERO_SPEND_MODE_HARD_REQUIRED')
    obj=json.loads(Path(args.observation_json).read_text(encoding='utf-8'))
    body=obj['request']
    url=body.get('screenshot_data_url','')
    if not (url.startswith('data:image/') and ',' in url):
        raise SystemExit('SCREENSHOT_DATA_URL_MISSING')

    first_key,first=run_once(body)
    second_key,second=run_once(body)
    if first_key!=second_key:
        raise SystemExit('LOCAL_ROUTE_SEMANTIC_REPLAY_MISMATCH:'+json.dumps({
            'first':first_key,'second':second_key},sort_keys=True))

    print(json.dumps({
        'status':'LOCAL_ROUTE_CONTRACT_REPLAY_PASS',
        'model':MODEL,
        'model_revision':MODEL_REVISION,
        'canonical_action':first_key,
        'first_attempt':first['attempts'][-1],
        'second_attempt':second['attempts'][-1],
        'zero_spend_mode':'HARD',
    },ensure_ascii=False,sort_keys=True))


if __name__=='__main__':
    main()
