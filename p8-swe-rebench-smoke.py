import json, os, re, subprocess, sys, tempfile, time, urllib.request, urllib.error, urllib.parse
from pathlib import Path
from datasets import load_dataset

DATASET = 'ibragim-bad/SWE-rebench-V2-sample'
MODEL = os.environ.get('MODEL_PATH', 'model.gguf')
LLAMA = os.environ.get('LLAMA_CLI', './llama-cli')
OUT = Path('p8-swe-artifact')
OUT.mkdir(exist_ok=True)

def run(cmd, cwd=None, timeout=600):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)

def clean_diff(text):
    text = re.sub(r'^```(?:diff)?\s*', '', text.strip(), flags=re.I)
    text = re.sub(r'\s*```$', '', text.strip())
    i = text.find('diff --git ')
    return text[i:] if i >= 0 else text

def select_context(repo, problem, limit=4, max_chars=24000):
    tokens = [x for x in re.findall(r'[A-Za-z_][A-Za-z0-9_]{3,}', problem.lower())
              if x not in {'this','that','with','from','when','have','should','into','there','which'}]
    files = run(['git','ls-files'], repo).stdout.splitlines()
    scored=[]
    for rel in files:
        if not re.search(r'\.(py|js|ts|tsx|jsx|c|cc|cpp|h|hpp|go|rs|java|rb)$', rel, re.I):
            continue
        if re.search(r'(^|/)(test|tests|nc_test|nc_test4)(/|_)', rel, re.I):
            continue
        score=sum(3 for t in tokens if t in rel.lower())
        scored.append((score, rel))
    scored.sort(reverse=True)
    picked=[]; used=0
    for _, rel in scored:
        try:
            text=Path(repo,rel).read_text(encoding='utf-8',errors='ignore')
        except Exception:
            continue
        hit=sum(text.lower().count(t) for t in tokens[:40])
        if hit==0 and picked:
            continue
        low=text.lower()
        positions=[low.find(t) for t in tokens[:60] if low.find(t)>=0]
        center=min(positions) if positions else 0
        start=max(0, center-3500)
        end=min(len(text), center+6500)
        chunk=text[start:end]
        block=f'FILE: {rel} [chars {start}:{end}]\n{chunk}\n'
        if used+len(block)>max_chars:
            break
        picked.append(block); used+=len(block)
        if len(picked)>=limit:
            break
    return '\n'.join(picked)

def fresh_oidc():
    url=os.environ.get('ACTIONS_ID_TOKEN_REQUEST_URL','')
    bearer=os.environ.get('ACTIONS_ID_TOKEN_REQUEST_TOKEN','')
    if url and bearer:
        sep='&' if '?' in url else '?'
        req=urllib.request.Request(url+sep+'audience='+urllib.parse.quote('arbm-sist-benchmark'))
        req.add_header('Authorization','Bearer '+bearer)
        with urllib.request.urlopen(req, timeout=20) as r:
            return str(json.loads(r.read().decode('utf-8'))['value'])
    return os.environ.get('ARBM_BENCHMARK_OIDC','')

def infer(prompt, instance_id):
    endpoint=os.environ.get('ARBM_BENCHMARK_ENDPOINT','')
    if endpoint:
        body=json.dumps({'task':prompt,'task_class':'swe-rebench-v2','instance_id':instance_id}).encode('utf-8')
        last_err=''
        for attempt, delay in enumerate((0, 20, 40), start=1):
            if delay:
                time.sleep(delay)
            try:
                token=fresh_oidc()
                if not token:
                    return 126, [], 'NO_OIDC_PROVIDER_TOKEN', False
                req=urllib.request.Request(endpoint, data=body, method='POST')
                req.add_header('Authorization', 'Bearer '+token)
                req.add_header('Content-Type', 'application/json')
                with urllib.request.urlopen(req, timeout=150) as r:
                    data=json.loads(r.read().decode('utf-8'))
                if not data.get('ok'):
                    last_err='REMOTE_STATUS:'+str(data.get('status'))
                    continue
                return 0, data.get('edits',[]), '', False
            except urllib.error.HTTPError as exc:
                error_body=exc.read().decode('utf-8','ignore')[:2000]
                last_err=f'HTTP {exc.code}: {error_body}'
                transient=(exc.code in (502,503,504) and ('high demand' in error_body.lower() or 'provider_timeout' in error_body.lower() or 'provider_error' in error_body.lower()))
                if transient and attempt < 3:
                    continue
                return 125, [], last_err, False
            except TimeoutError as exc:
                last_err=type(exc).__name__+': '+str(exc)
                if attempt < 3:
                    continue
                return 124, [], last_err, True
            except Exception as exc:
                return 125, [], type(exc).__name__+': '+str(exc), False
        return 125, [], last_err or 'REMOTE_RETRY_EXHAUSTED', False
    return 126, [], 'NO_REMOTE_PROVIDER', False

ds=load_dataset(DATASET, split='train')
row=dict(ds[0])
for secret in ('patch','test_patch','PASS_TO_PASS','FAIL_TO_PASS'):
    row.pop(secret, None)
repo_url='https://github.com/'+row['repo']+'.git'
base=row['base_commit']; iid=row['instance_id']; problem=row['problem_statement']
with tempfile.TemporaryDirectory(prefix='arbm-swe-') as td:
    r=run(['git','clone','--filter=blob:none','--no-checkout',repo_url,td], timeout=300)
    if r.returncode: raise SystemExit(r.stderr)
    r=run(['git','checkout',base], td, 180)
    if r.returncode: raise SystemExit(r.stderr)
    context=select_context(td,problem)
    prompt=(
      'You are ARBM SIST benchmark adapter. Solve the software issue using only the repository context. '
      'Return ONLY a valid unified git diff beginning with diff --git. Do not explain. '
      'Do not modify tests unless the issue explicitly requires it.\n\nISSUE:\n'+problem+
      '\n\nREPOSITORY CONTEXT:\n'+context)
    started=time.time(); code,edits,err,timed_out=infer(prompt,iid); latency=round((time.time()-started)*1000)
    edit_errors=[]; applied_edits=0
    if code==0 and isinstance(edits,list):
        for edit in edits:
            try:
                rel=str(edit.get('path','')).replace('\\','/').lstrip('/')
                old=str(edit.get('old','')); new=str(edit.get('new',''))
                target=Path(td,rel).resolve()
                if not str(target).startswith(str(Path(td).resolve())) or not target.is_file():
                    edit_errors.append('invalid_path:'+rel); continue
                text=target.read_text(encoding='utf-8',errors='strict')
                count=text.count(old)
                if count!=1:
                    edit_errors.append(f'old_match_count:{rel}:{count}'); continue
                target.write_text(text.replace(old,new,1),encoding='utf-8')
                applied_edits+=1
            except Exception as exc:
                edit_errors.append(type(exc).__name__+':'+str(exc)[:200])
    diff_run=run(['git','diff','--no-ext-diff','--binary'],td,60)
    patch=diff_run.stdout
    structure_valid=(code==0) and applied_edits>0 and patch.startswith('diff --git ') and len(patch)>40
    apply_check=False; apply_error=''
    if structure_valid:
        run(['git','reset','--hard',base],td,60)
        patch_file=Path(td,'arbm.patch'); patch_file.write_text(patch,encoding='utf-8')
        chk=run(['git','apply','--check',str(patch_file)],td,60)
        apply_check=(chk.returncode==0); apply_error=(chk.stderr or chk.stdout).strip()[:500]
    valid=structure_valid and apply_check and not edit_errors
    evidence={'schema':'arbm-p8-swe-smoke-v1','dataset':DATASET,'instance_id':iid,
      'repo':row['repo'],'base_commit':base,'model':os.environ.get('MODEL_LABEL','unknown'),'provider':os.environ.get('MODEL_PROVIDER','local-llama'),
      'latencyMs':latency,'exitCode':code,'validPatch':valid,'patchChars':len(patch),
      'stderrChars':len(err),'stderrPreview':err[:500],'timedOut':timed_out,'editCount':len(edits) if isinstance(edits,list) else 0,'appliedEdits':applied_edits,'editErrors':edit_errors[:8],'structureValid':structure_valid,'applyCheck':apply_check,'applyError':apply_error,'goldPatchExposedToAgent':False}
    Path(OUT,'agent-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    Path(OUT,'patches.json').write_text(json.dumps([{'instance_id':iid,'patch':patch}],indent=2)+'\n')
    Path(OUT,'instance.json').write_text(json.dumps({'instance_id':iid,'repo':row['repo'],'base_commit':base},indent=2)+'\n')
    if code or not valid:
        print(json.dumps(evidence)); raise SystemExit(2)
print(json.dumps(evidence))
