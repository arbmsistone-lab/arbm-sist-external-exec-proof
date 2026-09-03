import json, os, re, subprocess, sys, tempfile, time
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

def select_context(repo, problem, limit=4, max_chars=12000):
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
        chunk=text[:5000]
        block=f'FILE: {rel}\n{chunk}\n'
        if used+len(block)>max_chars:
            break
        picked.append(block); used+=len(block)
        if len(picked)>=limit:
            break
    return '\n'.join(picked)

def infer(prompt):
    cmd=[LLAMA,'-m',MODEL,'-p',prompt,'-n','700','--temp','0','--single-turn',
         '--simple-io','--no-display-prompt','--no-show-timings']
    try:
        proc=run(cmd, timeout=180)
        return proc.returncode, proc.stdout, proc.stderr, False
    except subprocess.TimeoutExpired as exc:
        out=exc.stdout or ''
        err=exc.stderr or ''
        if isinstance(out,bytes): out=out.decode('utf-8','ignore')
        if isinstance(err,bytes): err=err.decode('utf-8','ignore')
        return 124, out, err, True

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
    started=time.time(); code,out,err,timed_out=infer(prompt); latency=round((time.time()-started)*1000)
    patch=clean_diff(out)
    valid=(not timed_out) and patch.startswith('diff --git ') and len(patch)>40
    evidence={'schema':'arbm-p8-swe-smoke-v1','dataset':DATASET,'instance_id':iid,
      'repo':row['repo'],'base_commit':base,'model':os.environ.get('MODEL_LABEL','unknown'),
      'latencyMs':latency,'exitCode':code,'validPatch':valid,'patchChars':len(patch),
      'stderrChars':len(err),'timedOut':timed_out,'goldPatchExposedToAgent':False}
    Path(OUT,'agent-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    Path(OUT,'patches.json').write_text(json.dumps([{'instance_id':iid,'patch':patch}],indent=2)+'\n')
    Path(OUT,'instance.json').write_text(json.dumps({'instance_id':iid,'repo':row['repo'],'base_commit':base},indent=2)+'\n')
    if code or not valid:
        print(json.dumps(evidence)); raise SystemExit(2)
print(json.dumps(evidence))
