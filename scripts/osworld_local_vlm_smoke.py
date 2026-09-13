"""Cloud-only admission proof for the quota-independent local VLM."""
import base64
import json
from pathlib import Path
import sys

from osworld_local_vlm import LOCAL_VLM_ROUTE

root=Path(sys.argv[1])
pngs=sorted(root.glob('**/task-001/results/**/tasks/001/*.png'))
if not pngs: raise RuntimeError('REAL_RECORDED_SCREENSHOT_REQUIRED')
url='data:image/png;base64,'+base64.b64encode(pngs[0].read_bytes()).decode()
messages=[{'role':'system','content':'Return exactly YES or NO.'},
          {'role':'user','content':[{'type':'text','text':'Does this image show a full-screen photograph of a football field with football players? Return exactly YES or NO.'},
                                  {'type':'image_url','image_url':{'url':url}}]}]
result,attempts=LOCAL_VLM_ROUTE.call({},budget=240,raw_messages=messages,raw_tokens=8)
proof={'result':result,'attempts':attempts,'source_run':34733419571}
Path('osworld-v32-local-vlm-smoke.json').write_text(json.dumps(proof,indent=2))
if not result: raise RuntimeError('LOCAL_VLM_UNAVAILABLE')
verdict=result['text'].strip().upper().rstrip('.!')
if verdict!='NO': raise RuntimeError('LOCAL_VLM_BINARY_MISMATCH:'+repr(result['text']))
print('LOCAL_VLM_NEGATIVE_BINARY_PASS')
