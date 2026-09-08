import ast, json, os, re, urllib.error, urllib.parse, urllib.request
from pathlib import Path
SCRIPT=Path(__file__).with_name('p8-swe-rebench-smoke.py')
WANTED={'_compact_public_issue','_compact_public_context','_compact_public_validation_output','fresh_oidc','_sovereign_json'}
tree=ast.parse(SCRIPT.read_text(encoding='utf-8'))
scope={'json':json,'os':os,'re':re,'urllib':__import__('urllib'),'Path':Path}
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name in WANTED:
        module=ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[]))
        exec(compile(module,str(SCRIPT),'exec'),scope)
os.environ['ARBM_SOVEREIGN_ENDPOINT']='https://arbm-p0-free-proof.zevanory.workers.dev'
os.environ['ARBM_SOVEREIGN_AUTH']='github-oidc'
os.environ['ARBM_SOVEREIGN_TIMEOUT_SECONDS']='120'
payload={
    'phase':'solve',
    'issue':'In src/example.py, answer() must return 42 instead of 41. Make the smallest source fix.',
    'tool_context':'FILE: src/example.py\n000001|def answer():\n000002|    return 41',
}
code,data,err,timed=scope['_sovereign_json'](payload)
if code!=0: raise SystemExit('provider_failed:'+str(err)[:200])
edits=data.get('edits') if isinstance(data,dict) else None
if not isinstance(edits,list) or not edits: raise SystemExit('no_edits')
valid=[e for e in edits if isinstance(e,dict) and e.get('path')=='src/example.py' and 1<=int(e.get('start_line',0))<=int(e.get('end_line',0))<=2 and '42' in str(e.get('new',''))]
if not valid: raise SystemExit('unexpected_edit_shape')
evidence={
    'schema':'arbm-p3-cloudflare-swe-dev-smoke-v1','state':'PASS','scoreable':False,
    'model':data.get('model'),'pipeline':data.get('pipeline'),'mandatoryCostUsd':0,
    'paidFallbackUsed':False,'editCount':len(edits),'syntheticCase':'return-41-to-42',
    'goldPatchExposed':False,'hiddenEvaluatorUsed':False,
}
Path('p3-cloudflare-swe-dev-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
print(json.dumps(evidence))
