#!/usr/bin/env python3
import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0,str(HERE))

from osworld_local_vlm import MODEL, MODEL_REVISION, action_prompt, default_infer, parse_action_object


def main():
    p=argparse.ArgumentParser()
    p.add_argument('observation_json')
    p.add_argument('--expected-sha256',default='')
    args=p.parse_args()
    obj=json.loads(Path(args.observation_json).read_text(encoding='utf-8'))
    body=obj['request']
    url=body.get('screenshot_data_url','')
    if not (url.startswith('data:image/') and ',' in url):
        raise SystemExit('SCREENSHOT_DATA_URL_MISSING')
    image_b64=url.split(',',1)[1]
    prompt=action_prompt(body)
    output=default_infer(prompt,image_b64,96)
    raw=str(output or '')
    digest=hashlib.sha256(raw.encode()).hexdigest()
    record={
        'model':MODEL,
        'model_revision':MODEL_REVISION,
        'output_chars':len(raw),
        'output_sha256':digest,
        'output':raw,
    }
    try:
        record['parsed_action']=parse_action_object(raw,body.get('observation',''))
        record['contract_error']=''
    except ValueError as exc:
        record['parsed_action']=None
        record['contract_error']=str(exc)
    print(json.dumps(record,ensure_ascii=False,sort_keys=True))
    if args.expected_sha256 and digest!=args.expected_sha256:
        raise SystemExit(f'REPLAY_HASH_MISMATCH expected={args.expected_sha256} actual={digest}')

if __name__=='__main__':
    main()
