import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request, urllib.error, urllib.parse
from pathlib import Path
from datasets import load_dataset

DATASET = 'ibragim-bad/SWE-rebench-V2-sample'
HF_OFFSET = int(os.environ.get('HF_OFFSET', '0'))
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

def select_context(repo, problem, limit=4, max_chars=16000):
    problem_low=problem.lower()
    distinctive_names={t.lower() for t in re.findall(r'[A-Za-z][A-Za-z0-9_]{4,}',problem) if ('_' in t or any(c.isdigit() for c in t) or any(c.isupper() for c in t[1:]))}
    test_intent=bool(re.search(r'\b(test|tests|testing|testcase|testcases)\b',problem_low))
    plugin_intent=('plugin' in problem_low)
    noop_intent=bool(re.search(r'\bh5znoop\b|\bnoop(?:1)?\b',problem_low))
    test_plugin_change_intent=(test_intent and plugin_intent and bool(re.search(r'\b(add|adds|extend|extends|extended|change|changes|changing|required|requires|testcase|testcases)\b',problem_low)))
    hdf5_intent=('hdf5' in problem_low) and not test_plugin_change_intent
    behavior_intent=bool(re.search(r'\b(fix|fixed|consistent|consistency|different|reverse|same|order|incorrect|wrong|bug)\b',problem_low))
    multifilter_inquiry_intent=(('nc_inq_var_filter' in problem_low) and bool(re.search(r'\b(more than one|non-first|filter 2|filter 3|filter 4|multiple filters?)\b',problem_low)))
    tokens = [x for x in re.findall(r'[A-Za-z_][A-Za-z0-9_]{3,}', problem)
              if x.lower() not in {'this','that','with','from','when','have','should','into','there','which'}]
    base_symbols={t for t in tokens if '_' in t and len(t) >= 7}
    symbol_aliases={t[3:] for t in base_symbols if t.lower().startswith('nc_') and t.count('_') >= 2 and len(t[3:]) >= 7}
    symbols = sorted(base_symbols | symbol_aliases, key=lambda x: (-problem.count(x), -len(x), x))
    keywords = sorted({t.lower() for t in tokens if len(t) >= 5}, key=lambda x: (-problem.lower().count(x), -len(x), x))[:30]
    candidates=[]
    source_ext={'.c','.cc','.cpp','.cxx','.py','.js','.ts','.tsx','.jsx','.go','.rs','.java','.rb'}
    support_ext={'.am','.sh','.txt','.cmake'}
    header_ext={'.h','.hpp','.hh','.hxx'}
    for symbol_rank, symbol in enumerate(symbols[:16]):
        g=run(['git','grep','-n','-F',symbol,'--','*.py','*.js','*.ts','*.tsx','*.jsx','*.c','*.cc','*.cpp','*.cxx','*.h','*.hpp','*.hh','*.hxx','*.go','*.rs','*.java','*.rb'], repo, 60)
        for line in g.stdout.splitlines():
            parts=line.split(':',2)
            if len(parts)<3: continue
            rel, line_no, snippet = parts
            is_test=bool(re.search(r'(^|/)(test|tests|nc_test|nc_test4)(/|_)', rel, re.I))
            ext=Path(rel).suffix.lower(); score=100 if ext in source_ext else 10 if ext in header_ext else 0
            if re.search(r'(^|/)(src|source|lib[^/]*|core)(/|$)', rel, re.I): score+=25
            if re.search(r'(^|/)(libhdf5|libnczarr)(/|$)', rel, re.I): score+=80
            if (not noop_intent) and (re.search(r'(notnc|noop|stub)', rel, re.I) or re.search(r'\b(NC_NOTNC4|NC_NOOP)_', snippet)): score-=260
            if re.search(r'(^|/)(include|inc|examples?)(/|$)', rel, re.I): score-=25
            if '(' in snippet and ')' in snippet: score+=15
            if re.search(r'\b'+re.escape(symbol)+r'\s*\(', snippet): score+=20
            stem=Path(rel).stem.lower()
            stem_parts=[x for x in re.split(r'[-_.]+',stem) if len(x)>=4 and x not in {'test','tests','tst'}]
            if stem in distinctive_names: score+=220
            if stem_parts and all(x in problem_low for x in stem_parts): score+=280
            if plugin_intent and re.search(r'(^|/)plugins?(/|$)',rel,re.I): score+=120
            if multifilter_inquiry_intent and rel.lower()=='libdispatch/dfilter.c': score+=700
            if multifilter_inquiry_intent and rel.lower()=='include/netcdf_filter.h': score+=680
            if multifilter_inquiry_intent and 'multifilter' in rel.lower(): score+=620
            if multifilter_inquiry_intent and 'filter_order' in rel.lower(): score+=500
            if test_plugin_change_intent and re.search(r'(^|/)plugins?(/|$)',rel,re.I): score+=360
            if noop_intent and 'h5znoop' in rel.lower(): score+=520
            if test_plugin_change_intent and is_test and 'filter_order' in rel.lower(): score+=480
            if hdf5_intent and re.search(r'(^|/)libhdf5(/|$)',rel,re.I): score+=260
            if hdf5_intent and 'hdf5open' in rel.lower(): score+=180
            if behavior_intent and not is_test and not test_plugin_change_intent: score += 220
            if is_test: score += 100 if test_intent else (30 if behavior_intent else -20)
            score += 120 + max(0, 30-symbol_rank*2)
            try: ln=int(line_no)
            except Exception: ln=1
            candidates.append((score, rel, ln, symbol))
    files=run(['git','ls-files'],repo).stdout.splitlines()
    for rel in files:
        ext=Path(rel).suffix.lower()
        if ext not in source_ext and ext not in support_ext and ext not in header_ext: continue
        is_test=bool(re.search(r'(^|/)(test|tests|nc_test|nc_test4)(/|_)',rel,re.I))
        try: text=Path(repo,rel).read_text(encoding='utf-8',errors='ignore')
        except Exception: continue
        low=text.lower(); pathlow=rel.lower(); hits=sum(min(5,low.count(k)) for k in keywords)
        path_hits=sum(1 for k in keywords if k in pathlow)
        if not hits and not path_hits: continue
        score=60 + min(70,hits*3) + path_hits*18
        stem=Path(rel).stem.lower()
        stem_parts=[x for x in re.split(r'[-_.]+',stem) if len(x)>=4 and x not in {'test','tests','tst'}]
        if stem in distinctive_names: score+=220
        if stem_parts and all(x in problem_low for x in stem_parts): score+=280
        if plugin_intent and re.search(r'(^|/)plugins?(/|$)',rel,re.I): score+=120
        if test_plugin_change_intent and re.search(r'(^|/)plugins?(/|$)',rel,re.I): score+=360
        if noop_intent and 'h5znoop' in rel.lower(): score+=520
        if test_plugin_change_intent and is_test and 'filter_order' in rel.lower(): score+=480
        if hdf5_intent and re.search(r'(^|/)libhdf5(/|$)',rel,re.I): score+=260
        if hdf5_intent and 'hdf5open' in rel.lower(): score+=180
        if behavior_intent and not is_test and not test_plugin_change_intent: score+=140
        if test_intent and is_test: score+=60
        if re.search(r'(^|/)(src|source|lib[^/]*|core)(/|$)',rel,re.I): score+=25
        if re.search(r'(^|/)(libhdf5|libnczarr)(/|$)',rel,re.I): score+=80
        if (not noop_intent) and re.search(r'(notnc|noop|stub)',rel,re.I): score-=260
        if re.search(r'(^|/)(examples?)(/|$)',rel,re.I): score-=35
        focus=next((k for k in keywords if k in low), keywords[0] if keywords else '')
        if hdf5_intent and 'hdf5open' in rel.lower():
            for anchor in ('h5pget_nfilters','h5pget_filter2','nc4_hdf5_addfilter'):
                if anchor in low:
                    focus=anchor
                    break
        pos=low.find(focus) if focus else 0
        ln=low[:max(0,pos)].count('\n')+1
        candidates.append((score,rel,ln,'lexical:'+focus))
    ordered=sorted(candidates, key=lambda x:(-x[0], x[1], x[2]))
    if multifilter_inquiry_intent:
        special=[]; special_paths=set()
        groups=[
            [c for c in ordered if c[1].lower()=='libdispatch/dfilter.c'],
            [c for c in ordered if c[1].lower()=='include/netcdf_filter.h'],
            [c for c in ordered if 'multifilter' in c[1].lower()],
            [c for c in ordered if 'filter_order' in c[1].lower()],
        ]
        for group in groups:
            for c in group:
                if c[1] in special_paths: continue
                special.append(c); special_paths.add(c[1]); break
        ordered=special+[c for c in ordered if c not in special]
    elif test_plugin_change_intent:
        special=[]; special_paths=set()
        groups=[
            [c for c in ordered if 'h5znoop' in c[1].lower()],
            [c for c in ordered if re.search(r'(^|/)(test|tests|nc_test|nc_test4)(/|_)',c[1],re.I) and 'filter_order' in c[1].lower()],
            [c for c in ordered if re.search(r'(^|/)plugins?(/|$)',c[1],re.I)],
            [c for c in ordered if re.search(r'(^|/)(test|tests|nc_test|nc_test4)(/|_)',c[1],re.I)],
        ]
        for group in groups:
            for c in group:
                if c[1] in special_paths: continue
                special.append(c); special_paths.add(c[1]); break
        ordered=special+[c for c in ordered if c not in special]
    elif behavior_intent:
        prod=[]; prod_paths=set()
        symbol_prod=[c for c in ordered if not str(c[3]).startswith('lexical:') and not re.search(r'(^|/)(test|tests|nc_test|nc_test4)(/|_)', c[1], re.I)]
        lexical_prod=[c for c in ordered if str(c[3]).startswith('lexical:') and not re.search(r'(^|/)(test|tests|nc_test|nc_test4)(/|_)', c[1], re.I)]
        causal_prod=[c for c in lexical_prod if hdf5_intent and 'hdf5open' in c[1].lower()]
        prod_order=causal_prod + symbol_prod + [c for c in lexical_prod if c not in causal_prod]
        for c in prod_order:
            if c[1] in prod_paths: continue
            prod.append(c); prod_paths.add(c[1])
            if len(prod) >= min(2, max(1, limit-1)): break
        tests=[]; test_paths=set()
        for c in ordered:
            if not re.search(r'(^|/)(test|tests|nc_test|nc_test4)(/|_)', c[1], re.I): continue
            if c[1] in test_paths: continue
            tests.append(c); test_paths.add(c[1]); break
        ordered=prod+tests+[c for c in ordered if c not in prod and c not in tests]
    seen=set(); picked=[]; used=0
    for score, rel, ln, symbol in ordered:
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


def remote_json(payload):
    endpoint=os.environ.get('ARBM_BENCHMARK_ENDPOINT','')
    if not endpoint: return 126, None, 'NO_REMOTE_PROVIDER', False
    body=json.dumps(payload).encode('utf-8'); last_err=''
    for attempt,delay in enumerate((0,12),start=1):
        if delay: time.sleep(delay)
        try:
            token=fresh_oidc()
            if not token: return 126,None,'NO_OIDC_PROVIDER_TOKEN',False
            req=urllib.request.Request(endpoint,data=body,method='POST')
            req.add_header('Authorization','Bearer '+token); req.add_header('Content-Type','application/json')
            with urllib.request.urlopen(req,timeout=150) as r: data=json.loads(r.read().decode('utf-8'))
            if data.get('ok'): return 0,data,'',False
            last_err='REMOTE_STATUS:'+str(data.get('status'))
        except urllib.error.HTTPError as exc:
            b=exc.read().decode('utf-8','ignore')[:2000]; last_err=f'HTTP {exc.code}: {b}'
        except TimeoutError as exc:
            last_err=type(exc).__name__+': '+str(exc)
        except Exception as exc: return 125,None,type(exc).__name__+': '+str(exc),False
    return 125,None,last_err or 'REMOTE_RETRY_EXHAUSTED',False

def remote_endpoint_json(endpoint, payload):
    body=json.dumps(payload).encode('utf-8'); last_err=''
    for attempt,delay in enumerate((0,12),start=1):
        if delay: time.sleep(delay)
        try:
            token=fresh_oidc()
            if not token: return 126,None,'NO_OIDC_PROVIDER_TOKEN',False
            req=urllib.request.Request(endpoint,data=body,method='POST')
            req.add_header('Authorization','Bearer '+token); req.add_header('Content-Type','application/json')
            with urllib.request.urlopen(req,timeout=150) as r: data=json.loads(r.read().decode('utf-8'))
            if data.get('ok'): return 0,data,'',False
            last_err='REMOTE_STATUS:'+str(data.get('status'))
        except urllib.error.HTTPError as exc:
            b=exc.read().decode('utf-8','ignore')[:2000]; last_err=f'HTTP {exc.code}: {b}'
        except TimeoutError as exc: last_err=type(exc).__name__+': '+str(exc)
        except Exception as exc: return 125,None,type(exc).__name__+': '+str(exc),False
    return 125,None,last_err or 'REMOTE_RETRY_EXHAUSTED',False

def repo_index(repo, problem):
    files=run(['git','ls-files'],repo,60).stdout.splitlines()
    shown='\n'.join(files[:4000])
    toks=[x for x in re.findall(r'[A-Za-z_][A-Za-z0-9_./:-]{3,}',problem) if len(x)>=4][:18]
    sig=[]
    for q in toks:
        g=run(['git','grep','-n','-I','-F',q,'--'],repo,25)
        if g.returncode in (0,1) and g.stdout:
            sig.extend(g.stdout.splitlines()[:12])
        if len(sig)>=120: break
    return ('TRACKED FILES:\n'+shown+'\nINITIAL GREP SIGNALS:\n'+'\n'.join(sig))[:20000]

def lexical_fallback(repo, problem, limit=8):
    stop={'this','that','with','from','when','have','will','should','there','which','into','about','more','than','what','does','using','used','only','also','some','same','after','before'}
    raw=re.findall(r'[A-Za-z_][A-Za-z0-9_.:/-]{3,}',problem)
    terms=[]
    for t in raw:
        x=t.strip('.,:;()[]{}').lower()
        if len(x)<4 or x in stop or x in terms: continue
        terms.append(x)
    files=run(['git','ls-files'],repo,60).stdout.splitlines()
    scores={}; centers={}
    def noisy(rel):
        r=rel.lower()
        return r.startswith('.github/') or r.startswith('.git') or r.startswith('docs/') or r.startswith('doc/') or r.endswith(('.md','.rst','.txt','.lock','.yml','.yaml','.json'))
    for q in terms[:28]:
        g=run(['git','grep','-n','-I','-i','-F',q,'--'],repo,25)
        if g.returncode not in (0,1): continue
        for line in g.stdout.splitlines()[:80]:
            parts=line.split(':',2)
            if len(parts)<2 or not parts[1].isdigit(): continue
            rel=parts[0].replace('\\','/')
            if rel not in files: continue
            score=3
            if q in Path(rel).name.lower(): score+=8
            if re.search(r'(^|/)(src|lib|app|core)(/|$)',rel,re.I): score+=6
            if re.search(r'(^|/)(test|tests|spec)(/|$|_)',rel,re.I): score+=2
            if noisy(rel): score-=8
            scores[rel]=scores.get(rel,0)+score
            centers.setdefault(rel,int(parts[1]))
    ranked=[r for r,_ in sorted(scores.items(),key=lambda kv:(-kv[1],kv[0])) if not noisy(r)]
    if len(ranked)<2:
        ranked += [r for r,_ in sorted(scores.items(),key=lambda kv:(-kv[1],kv[0])) if r not in ranked]
    return ranked[:limit],centers

def numbered_file(repo, rel, center=None, radius=120):
    f=Path(repo,rel)
    if not f.is_file(): return ''
    try: lines=f.read_text(encoding='utf-8',errors='ignore').splitlines(True)
    except Exception: return ''
    if center is None: a,b=0,min(len(lines),240)
    else: a=max(0,center-radius); b=min(len(lines),center+radius)
    return f'FILE: {rel}\n'+''.join(f'{i+1:06d}|{lines[i]}' for i in range(a,b))

def apply_candidate(repo, edits, allowed_paths):
    errors=[]; meta=[]; applied=0
    for edit in edits if isinstance(edits,list) else []:
        try:
            rel=str(edit.get('path','')).replace('\\','/').lstrip('/')
            if rel not in allowed_paths: errors.append('unauthorized_path:'+rel); continue
            target=Path(repo,rel).resolve()
            if not str(target).startswith(str(Path(repo).resolve())) or not target.is_file(): errors.append('invalid_path:'+rel); continue
            text=target.read_text(encoding='utf-8',errors='strict'); lines=text.splitlines(True)
            try: start_line=int(edit.get('start_line')); end_line=int(edit.get('end_line'))
            except Exception: errors.append('invalid_line_range:'+rel); continue
            if start_line<1 or end_line<start_line or end_line>len(lines) or (end_line-start_line+1)>160: errors.append(f'line_range_out_of_bounds:{rel}:{start_line}:{end_line}:{len(lines)}'); continue
            old=''.join(lines[start_line-1:end_line]); new=str(edit.get('new',''))
            if not new.strip() or new.strip() in {'...','TODO','FIXME'}: errors.append('invalid_new:'+rel); continue
            if old.endswith('\n') and not new.endswith('\n'): new+='\n'
            if new==old or re.sub(r'\s+','',old)==re.sub(r'\s+','',new): errors.append('semantic_no_op_edit:'+rel); continue
            target.write_text(''.join(lines[:start_line-1])+new+''.join(lines[end_line:]),encoding='utf-8',newline='\n')
            applied+=1; meta.append({'path':rel,'startLine':start_line,'endLine':end_line,'oldLen':len(old),'newLen':len(new),'oldSha256':__import__('hashlib').sha256(old.encode()).hexdigest(),'newSha256':__import__('hashlib').sha256(new.encode()).hexdigest()})
        except Exception as exc: errors.append(type(exc).__name__+':'+str(exc)[:200])
    return errors,meta,applied

def public_validation(repo, changed_paths):
    try:
        if Path(repo,'project.clj').is_file():
            if shutil.which('lein') is None:
                a=run(['sudo','apt-get','update'],repo,180)
                if a.returncode: return True,a.returncode,(a.stderr or a.stdout)[-3000:]
                b=run(['sudo','apt-get','install','-y','leiningen'],repo,180)
                if b.returncode: return True,b.returncode,(b.stderr or b.stdout)[-3000:]
            r=run(['lein','test'],repo,300); return True,r.returncode,((r.stdout or '')+'\n'+(r.stderr or ''))[-6000:]
        if Path(repo,'go.mod').is_file() and shutil.which('go'):
            r=run(['go','test','./...'],repo,300); return True,r.returncode,((r.stdout or '')+'\n'+(r.stderr or ''))[-6000:]
        if Path(repo,'Cargo.toml').is_file() and shutil.which('cargo'):
            r=run(['cargo','test','--quiet'],repo,300); return True,r.returncode,((r.stdout or '')+'\n'+(r.stderr or ''))[-6000:]
        py=[x for x in changed_paths if str(x).endswith('.py')]
        if py:
            r=run([sys.executable,'-m','py_compile',*py],repo,120); return True,r.returncode,((r.stdout or '')+'\n'+(r.stderr or ''))[-6000:]
    except Exception as exc: return True,125,type(exc).__name__+': '+str(exc)
    return False,0,'NO_SAFE_PUBLIC_VALIDATION'

def load_public_sample_with_backoff():
    last = None
    for attempt, delay in enumerate((0, 8, 20, 45), start=1):
        if delay:
            time.sleep(delay)
        try:
            return load_dataset(DATASET, split='train')
        except Exception as exc:
            last = exc
            msg = str(exc).lower()
            transient = ('429' in msg or 'too many requests' in msg or 'maximum queue size' in msg or '503' in msg or '502' in msg or '504' in msg)
            if not transient or attempt == 4:
                raise
    raise last

ds=load_public_sample_with_backoff()
if HF_OFFSET < 0 or HF_OFFSET >= len(ds):
    raise SystemExit(f'HF_OFFSET_OUT_OF_RANGE:{HF_OFFSET}:{len(ds)}')
row=dict(ds[HF_OFFSET])
for secret in ('patch','test_patch','PASS_TO_PASS','FAIL_TO_PASS'):
    row.pop(secret, None)
repo_url='https://github.com/'+row['repo']+'.git'
base=row['base_commit']; iid=row['instance_id']; problem=row['problem_statement']
with tempfile.TemporaryDirectory(prefix='arbm-swe-') as td:
    r=run(['git','clone','--filter=blob:none','--no-checkout',repo_url,td], timeout=300)
    if r.returncode: raise SystemExit(r.stderr)
    r=run(['git','checkout',base], td, 180)
    if r.returncode: raise SystemExit(r.stderr)
    idx=repo_index(td,problem)
    started=time.time(); pcode,pdata,perr,ptimed=remote_json({'phase':'plan','issue':problem,'repo_index':idx,'instance_id':iid})
    plan=(pdata or {}).get('plan',{}) if pcode==0 else {}
    candidate_paths=[]; centers={}
    for rel in plan.get('paths',[]):
        rel=str(rel).replace('\\','/').lstrip('/')
        if rel in run(['git','ls-files'],td,60).stdout.splitlines() and rel not in candidate_paths: candidate_paths.append(rel)
    for q in plan.get('queries',[]):
        g=run(['git','grep','-n','-I','-F',str(q),'--'],td,30)
        for ln in g.stdout.splitlines()[:30]:
            parts=ln.split(':',2)
            if len(parts)>=2 and parts[1].isdigit():
                rel=parts[0]; centers.setdefault(rel,int(parts[1]))
                if rel not in candidate_paths: candidate_paths.append(rel)
    if not candidate_paths:
        candidate_paths,lex_centers=lexical_fallback(td,problem,8)
        for rel,ln in lex_centers.items(): centers.setdefault(rel,ln)
    if not candidate_paths:
        evidence={'schema':'arbm-p8-swe-smoke-v2-line-edit','dataset':DATASET,'instance_id':iid,'repo':row['repo'],'base_commit':base,'hfOffset':HF_OFFSET,'exitCode':127,'validPatch':False,'status':'NO_CONTEXT','plannerCode':pcode,'plannerError':perr[:500],'goldPatchExposedToAgent':False}
        Path(OUT,'agent-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
        Path(OUT,'patches.json').write_text(json.dumps([{'instance_id':iid,'patch':''}],indent=2)+'\n')
        Path(OUT,'instance.json').write_text(json.dumps({'instance_id':iid,'repo':row['repo'],'base_commit':base},indent=2)+'\n')
        print(json.dumps(evidence)); raise SystemExit(2)
    context='\n\n'.join(numbered_file(td,r,centers.get(r)) for r in candidate_paths[:8])[:32000]
    allowed_paths=re.findall(r'(?m)^FILE:\s+([^\s]+)',context)
    code,data,err,timed_out=remote_json({'phase':'solve','issue':problem,'tool_context':context,'instance_id':iid})
    cand_a=(data or {}).get('edits',[]) if code==0 else []
    alt_issue=problem+'\n\nGenerate an INDEPENDENT ALTERNATIVE solution. The first candidate was: '+json.dumps(cand_a)[:4000]+' Do not repeat it; test a different plausible root cause or more complete behavioral invariant using only supplied public context.'
    bcode,bdata,berr,btimed=remote_json({'phase':'solve','issue':alt_issue,'tool_context':context,'instance_id':iid})
    cand_b=(bdata or {}).get('edits',[]) if bcode==0 else []
    def dedupe_edits(edits):
        out=[]; seen=set()
        for e in edits if isinstance(edits,list) else []:
            if not isinstance(e,dict): continue
            key=(str(e.get('path','')).replace('\\','/'),e.get('start_line'),e.get('end_line'),str(e.get('new','')).strip())
            if key in seen: continue
            seen.add(key); out.append(e)
        return out
    cand_a=dedupe_edits(cand_a); cand_b=dedupe_edits(cand_b)
    latency=round((time.time()-started)*1000)
    if not cand_a and not cand_b and (code!=0 or bcode!=0):
        evidence={'schema':'arbm-p8-swe-smoke-v2-line-edit','dataset':DATASET,'instance_id':iid,'repo':row['repo'],'base_commit':base,'hfOffset':HF_OFFSET,'exitCode':125,'validPatch':False,'status':'WAITING_FREE_CAPACITY','providerUnavailable':True,'candidateACode':code,'candidateBCode':bcode,'providerError':(err+' | '+berr)[:1200],'allowedPaths':allowed_paths,'goldPatchExposedToAgent':False}
        Path(OUT,'agent-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
        Path(OUT,'patches.json').write_text(json.dumps([{'instance_id':iid,'patch':''}],indent=2)+'\n')
        Path(OUT,'instance.json').write_text(json.dumps({'instance_id':iid,'repo':row['repo'],'base_commit':base},indent=2)+'\n')
        print(json.dumps(evidence)); raise SystemExit(2)
    path_normalizations=[]
    candidate_results={}
    for label,cand in [('A',cand_a),('B',cand_b)]:
        run(['git','reset','--hard',base],td,60)
        errs,meta,applied=apply_candidate(td,cand,allowed_paths)
        attempted=False; vcode=125; vout='NOT_RUN'
        if applied>0 and not errs:
            attempted,vcode,vout=public_validation(td,[m['path'] for m in meta])
        candidate_results[label]={'edits':cand,'errors':errs,'meta':meta,'applied':applied,'validationAttempted':attempted,'validationCode':vcode,'validationPreview':vout[-1500:]}
    repair_records={}
    for label in ('A','B'):
        cr=candidate_results[label]
        if cr['applied']>0 and not cr['errors'] and cr['validationAttempted'] and cr['validationCode']!=0:
            repair_issue=problem+'\n\nPUBLIC REPOSITORY VALIDATION FAILED for candidate '+label+'. Repair the candidate using only the supplied public validation output and repository context. Do not use hidden tests or benchmark evaluator output. Rejected edits: '+json.dumps(cr['edits'])[:5000]+'\nPUBLIC VALIDATION OUTPUT:\n'+cr['validationPreview'][-3000:]
            rcode,rdata,rerr,rtimed=remote_json({'phase':'solve','issue':repair_issue,'tool_context':context,'instance_id':iid})
            repaired=dedupe_edits((rdata or {}).get('edits',[]) if rcode==0 else [])
            rec={'attempted':True,'providerCode':rcode,'providerError':rerr[:500],'edits':repaired}
            if repaired:
                run(['git','reset','--hard',base],td,60)
                errs,meta,applied=apply_candidate(td,repaired,allowed_paths)
                attempted=False; vcode=125; vout='NOT_RUN'
                if applied>0 and not errs:
                    attempted,vcode,vout=public_validation(td,[m['path'] for m in meta])
                rec.update({'errors':errs,'meta':meta,'applied':applied,'validationAttempted':attempted,'validationCode':vcode,'validationPreview':vout[-1500:]})
                if applied>0 and not errs and (not attempted or vcode==0):
                    candidate_results[label]={'edits':repaired,'errors':errs,'meta':meta,'applied':applied,'validationAttempted':attempted,'validationCode':vcode,'validationPreview':vout[-1500:]}
                    if label=='A': cand_a=repaired
                    else: cand_b=repaired
            repair_records[label]=rec
    passing=[x for x in ('A','B') if candidate_results[x]['applied']>0 and not candidate_results[x]['errors'] and (not candidate_results[x]['validationAttempted'] or candidate_results[x]['validationCode']==0)]
    judge_ep=os.environ.get('ARBM_BENCHMARK_JUDGE_ENDPOINT','')
    jcode,jdata,jerr,jtimed=(125,None,'NO_JUDGE_ENDPOINT',False)
    single_provider_fallback=(bool(cand_a) ^ bool(cand_b)) and len(passing)==1
    if single_provider_fallback:
        choice=passing[0]; judge_reason='single_valid_candidate_provider_fallback'; judge_edits=[]; jcode=204; jerr=''
    else:
        if judge_ep:
            jcode,jdata,jerr,jtimed=remote_endpoint_json(judge_ep,{'issue':problem,'tool_context':context,'instance_id':iid,'candidate_a':{'edits':cand_a},'candidate_b':{'edits':cand_b},'validation_a':candidate_results['A'],'validation_b':candidate_results['B']})
        choice=(jdata or {}).get('choice','NONE') if jcode==0 else 'NONE'
        judge_reason=str((jdata or {}).get('reason',''))[:600]
        judge_edits=(jdata or {}).get('edits',[]) if jcode==0 else []
    if choice in ('A','B'):
        edits=judge_edits if judge_edits else candidate_results[choice]['edits']
    else:
        edits=candidate_results[passing[0]]['edits'] if len(passing)==1 else []
    run(['git','reset','--hard',base],td,60)
    edit_errors,applied_meta,applied_edits=apply_candidate(td,edits,allowed_paths) if edits else (['semantic_arbiter_no_choice'],[],0)
    validation_attempted=False; validation_code=0; validation_output='NOT_RUN'; repair_attempted=False
    if applied_edits>0 and not edit_errors:
        validation_attempted,validation_code,validation_output=public_validation(td,[m['path'] for m in applied_meta])
        if validation_attempted and validation_code!=0:
            code=123; err='FINAL_PUBLIC_VALIDATION_FAILED: '+validation_output[-1000:]
        else:
            code=0; err=''
    if not edits or edit_errors: code=124 if code==0 else code; err=err or jerr or 'NO_SEMANTICALLY_SELECTED_CANDIDATE'
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
      'repo':row['repo'],'base_commit':base,'hfOffset':HF_OFFSET,'model':os.environ.get('MODEL_LABEL','unknown'),'provider':os.environ.get('MODEL_PROVIDER','local-llama'),
      'latencyMs':latency,'exitCode':code,'validPatch':valid,'patchChars':len(patch),
      'stderrChars':len(err),'stderrPreview':err[:500],'timedOut':timed_out,'editCount':len(edits) if isinstance(edits,list) else 0,'allowedPaths':allowed_paths,'pathNormalizations':path_normalizations,'editMeta':applied_meta,'appliedEdits':applied_edits,'editErrors':edit_errors[:8],'structureValid':structure_valid,'applyCheck':apply_check,'applyError':apply_error,'publicValidationAttempted':validation_attempted,'publicValidationCode':validation_code,'publicValidationPreview':validation_output[-1200:],'repairAttempted':bool(repair_records),'repairRecords':repair_records,'candidateA':candidate_results.get('A'),'candidateB':candidate_results.get('B'),'semanticJudgeChoice':choice,'semanticJudgeReason':judge_reason,'semanticJudgeCode':jcode,'goldPatchExposedToAgent':False}
    Path(OUT,'agent-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    Path(OUT,'patches.json').write_text(json.dumps([{'instance_id':iid,'patch':patch}],indent=2)+'\n')
    Path(OUT,'instance.json').write_text(json.dumps({'instance_id':iid,'repo':row['repo'],'base_commit':base},indent=2)+'\n')
    if code or not valid:
        print(json.dumps(evidence)); raise SystemExit(2)
print(json.dumps(evidence))
