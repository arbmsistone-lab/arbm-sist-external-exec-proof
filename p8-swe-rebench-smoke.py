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

def select_context(repo, problem, limit=4, max_chars=14000):
    tokens = [x for x in re.findall(r'[A-Za-z_][A-Za-z0-9_]{3,}', problem)
              if x.lower() not in {'this','that','with','from','when','have','should','into','there','which'}]
    symbols = sorted({t for t in tokens if '_' in t and len(t) >= 7}, key=lambda x: (-problem.count(x), -len(x), x))
    keywords = sorted({t.lower() for t in tokens if len(t) >= 5}, key=lambda x: (-problem.lower().count(x), -len(x), x))[:30]
    candidates=[]
    source_ext={'.c','.cc','.cpp','.cxx','.py','.js','.ts','.tsx','.jsx','.go','.rs','.java','.rb'}
    header_ext={'.h','.hpp','.hh','.hxx'}
    for symbol_rank, symbol in enumerate(symbols[:16]):
        g=run(['git','grep','-n','-F',symbol,'--','*.py','*.js','*.ts','*.tsx','*.jsx','*.c','*.cc','*.cpp','*.cxx','*.h','*.hpp','*.hh','*.hxx','*.go','*.rs','*.java','*.rb'], repo, 60)
        for line in g.stdout.splitlines():
            parts=line.split(':',2)
            if len(parts)<3: continue
            rel, line_no, snippet = parts
            if re.search(r'(^|/)(test|tests|nc_test|nc_test4)(/|_)', rel, re.I): continue
            ext=Path(rel).suffix.lower(); score=100 if ext in source_ext else 10 if ext in header_ext else 0
            if re.search(r'(^|/)(src|source|lib|libhdf5|core)(/|$)', rel, re.I): score+=25
            if re.search(r'(^|/)(include|inc|examples?)(/|$)', rel, re.I): score-=25
            if '(' in snippet and ')' in snippet: score+=15
            if re.search(r'\b'+re.escape(symbol)+r'\s*\(', snippet): score+=20
            score += max(0, 30-symbol_rank*2)
            try: ln=int(line_no)
            except Exception: ln=1
            candidates.append((score, rel, ln, symbol))
    files=run(['git','ls-files'],repo).stdout.splitlines()
    for rel in files:
        ext=Path(rel).suffix.lower()
        if ext not in source_ext: continue
        if re.search(r'(^|/)(test|tests|nc_test|nc_test4)(/|_)',rel,re.I): continue
        try: text=Path(repo,rel).read_text(encoding='utf-8',errors='ignore')
        except Exception: continue
        low=text.lower(); pathlow=rel.lower(); hits=sum(min(5,low.count(k)) for k in keywords)
        path_hits=sum(1 for k in keywords if k in pathlow)
        if not hits and not path_hits: continue
        score=60 + min(70,hits*3) + path_hits*18
        if re.search(r'(^|/)(src|source|lib|libhdf5|core)(/|$)',rel,re.I): score+=25
        if re.search(r'(^|/)(examples?)(/|$)',rel,re.I): score-=35
        focus=next((k for k in keywords if k in low), keywords[0] if keywords else '')
        pos=low.find(focus) if focus else 0
        ln=low[:max(0,pos)].count('\n')+1
        candidates.append((score,rel,ln,'lexical:'+focus))
    seen=set(); picked=[]; used=0
    for score, rel, ln, symbol in sorted(candidates, key=lambda x:(-x[0], x[1], x[2])):
        if rel in seen: continue
        seen.add(rel)
        try: text=Path(repo,rel).read_text(encoding='utf-8',errors='ignore')
        except Exception: continue
        lines=text.splitlines(True); start_line=max(0,ln-70); end_line=min(len(lines),ln+110)
        chunk=''.join(f'{i+1:06d}|{lines[i]}' for i in range(start_line,end_line))
        if len(chunk)>max_chars-used: chunk=chunk[:max_chars-used]
        if not chunk: continue
        picked.append(f'FILE: {rel} [signal {symbol}; score {score}; lines {start_line+1}:{end_line}]\n{chunk}\n')
        used+=len(chunk)
        if len(picked)>=limit or used>=max_chars: break
    return '\n'.join(picked) if picked else _fallback_context(repo, [t.lower() for t in tokens], limit, max_chars)

def _fallback_context(repo, tokens, limit=2, max_chars=10000):
    files=run(['git','ls-files'],repo).stdout.splitlines(); ranked=[]
    for rel in files:
        if not re.search(r'\.(py|js|ts|tsx|jsx|c|cc|cpp|h|hpp|go|rs|java|rb)$',rel,re.I): continue
        if re.search(r'(^|/)(test|tests|nc_test|nc_test4)(/|_)',rel,re.I): continue
        try: text=Path(repo,rel).read_text(encoding='utf-8',errors='ignore')
        except Exception: continue
        hits=sum(text.lower().count(t) for t in tokens[:30])
        if hits: ranked.append((hits,rel,text))
    ranked.sort(reverse=True); picked=[]; used=0
    for _,rel,text in ranked[:limit]:
        chunk=text[:min(5000,max_chars-used)]; picked.append(f'FILE: {rel}\n{chunk}\n'); used+=len(chunk)
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
        for attempt, delay in enumerate((0, 15), start=1):
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
                if transient and attempt < 2:
                    continue
                return 125, [], last_err, False
            except TimeoutError as exc:
                last_err=type(exc).__name__+': '+str(exc)
                if attempt < 2:
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
      'Return the smallest semantic line edit using path, start_line, end_line, new. Context lines are prefixed as NNNNNN|. The runner extracts OLD itself and generates the Git diff. NEW must make a real behavioral fix; never return a no-op edit. '
      'Do not modify tests unless the issue explicitly requires it.\n\nISSUE:\n'+problem+
      '\n\nREPOSITORY CONTEXT:\n'+context)
    allowed_paths=re.findall(r'(?m)^FILE:\s+([^\s]+)',context)
    started=time.time(); code,edits,err,timed_out=infer(prompt,iid); latency=round((time.time()-started)*1000)
    edit_errors=[]; applied_edits=0; path_normalizations=[]
    applied_meta=[]
    if code==0 and isinstance(edits,list):
        for edit in edits:
            try:
                rel=str(edit.get('path','')).replace('\\','/').lstrip('/')
                if rel not in allowed_paths:
                    edit_errors.append('unauthorized_path:'+rel); continue
                target=Path(td,rel).resolve()
                if not str(target).startswith(str(Path(td).resolve())) or not target.is_file():
                    edit_errors.append('invalid_path:'+rel); continue
                text=target.read_text(encoding='utf-8',errors='strict')
                lines=text.splitlines(True)
                try: start_line=int(edit.get('start_line')); end_line=int(edit.get('end_line'))
                except Exception:
                    edit_errors.append('invalid_line_range:'+rel); continue
                if start_line < 1 or end_line < start_line or end_line > len(lines) or (end_line-start_line+1) > 160:
                    edit_errors.append(f'line_range_out_of_bounds:{rel}:{start_line}:{end_line}:{len(lines)}'); continue
                old=''.join(lines[start_line-1:end_line]); new=str(edit.get('new',''))
                if not new.strip() or new.strip() in {'...','TODO','FIXME'}:
                    edit_errors.append('invalid_new:'+rel); continue
                if old.endswith('\n') and not new.endswith('\n'): new += '\n'
                if new == old:
                    edit_errors.append('no_op_edit:'+rel); continue
                replacement=''.join(lines[:start_line-1])+new+''.join(lines[end_line:])
                target.write_text(replacement,encoding='utf-8',newline='\n')
                applied_edits+=1
                applied_meta.append({'path':rel,'startLine':start_line,'endLine':end_line,'oldLen':len(old),'newLen':len(new),'oldSha256':__import__('hashlib').sha256(old.encode()).hexdigest(),'newSha256':__import__('hashlib').sha256(new.encode()).hexdigest()})
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
    evidence={'schema':'arbm-p8-swe-smoke-v2-line-edit','dataset':DATASET,'instance_id':iid,
      'repo':row['repo'],'base_commit':base,'model':os.environ.get('MODEL_LABEL','unknown'),'provider':os.environ.get('MODEL_PROVIDER','local-llama'),
      'latencyMs':latency,'exitCode':code,'validPatch':valid,'patchChars':len(patch),
      'stderrChars':len(err),'stderrPreview':err[:500],'timedOut':timed_out,'editCount':len(edits) if isinstance(edits,list) else 0,'allowedPaths':allowed_paths,'pathNormalizations':path_normalizations,'editMeta':applied_meta,'appliedEdits':applied_edits,'editErrors':edit_errors[:8],'structureValid':structure_valid,'applyCheck':apply_check,'applyError':apply_error,'goldPatchExposedToAgent':False}
    Path(OUT,'agent-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    Path(OUT,'patches.json').write_text(json.dumps([{'instance_id':iid,'patch':patch}],indent=2)+'\n')
    Path(OUT,'instance.json').write_text(json.dumps({'instance_id':iid,'repo':row['repo'],'base_commit':base},indent=2)+'\n')
    if code or not valid:
        print(json.dumps(evidence)); raise SystemExit(2)
print(json.dumps(evidence))
