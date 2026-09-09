import json, os
from huggingface_hub import HfApi

TOKEN=os.environ.get('HF_TOKEN','').strip()
if not TOKEN: raise SystemExit('HF_TOKEN_MISSING')
api=HfApi(token=TOKEN)
me=api.whoami()
user=me.get('name') or me.get('fullname')
repo=f'{user}/arbm-sist-free-capacity-probe'
api.create_repo(repo, repo_type='space', space_sdk='gradio', private=False, exist_ok=True)
app='''import gradio as gr\ndef ping(text): return {"ok": True, "echo": str(text)[:80]}\ndemo=gr.Interface(fn=ping, inputs="text", outputs="json")\nif __name__ == "__main__": demo.launch()\n'''
api.upload_file(path_or_fileobj=app.encode(), path_in_repo='app.py', repo_id=repo, repo_type='space', commit_message='add safe eligibility probe')
try:
    api.request_space_hardware(repo_id=repo, hardware='zero-a10g')
    rt=api.get_space_runtime(repo_id=repo)
    out={'status':'PASS','repo':repo,'stage':str(rt.stage),'hardware':str(rt.hardware),'requested_hardware':str(rt.requested_hardware),'mandatory_cost_usd':0,'paid_fallback_used':False}
except Exception as e:
    out={'status':'DENIED','repo':repo,'error_type':type(e).__name__,'error':str(e)[:300],'mandatory_cost_usd':0,'paid_fallback_used':False}
print(json.dumps(out,separators=(',',':')))
if out['status']!='PASS': raise SystemExit(2)
