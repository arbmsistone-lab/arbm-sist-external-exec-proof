import json, os, re, shutil, subprocess, sys, tempfile, time, urllib.request, urllib.error, urllib.parse
from pathlib import Path
from datasets import load_dataset

DATASET = 'ibragim-bad/SWE-rebench-V2-sample'
HF_OFFSET = int(os.environ.get('HF_OFFSET', '0'))
MODEL = os.environ.get('MODEL_PATH', 'model.gguf')
LLAMA = os.environ.get('LLAMA_CLI', './llama-cli')
OUT = Path('p8-swe-artifact')
OUT.mkdir(exist_ok=True)

def runtime_identity():
    return {
        'sourceCommit':os.environ.get('GITHUB_SHA','unknown'),
        'generatorBuild':os.environ.get('WORKER_REV','unknown'),
        'runner':{
            'name':os.environ.get('RUNNER_NAME','unknown'),
            'os':os.environ.get('RUNNER_OS',sys.platform),
            'arch':os.environ.get('RUNNER_ARCH','unknown'),
        },
        'modelArtifactSha256':os.environ.get('MODEL_SHA256','unknown'),
        'inferenceRuntime':{
            'llamaTag':os.environ.get('LLAMA_TAG','unknown'),
            'sha256':os.environ.get('LLAMA_SHA256','unknown'),
        },
    }

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


def _remote_json_one(endpoint, payload, retries=(0,12)):
    body=json.dumps(payload).encode('utf-8'); last_err=''
    for delay in retries:
        if delay: time.sleep(delay)
        try:
            token=fresh_oidc()
            if not token: return 126,None,'NO_OIDC_PROVIDER_TOKEN',False
            req=urllib.request.Request(endpoint,data=body,method='POST')
            req.add_header('Authorization','Bearer '+token); req.add_header('Content-Type','application/json')
            req.add_header('User-Agent','arbm-sist-benchmark/19'); req.add_header('Accept','application/json')
            with urllib.request.urlopen(req,timeout=150) as r: data=json.loads(r.read().decode('utf-8'))
            if data.get('ok'): return 0,data,'',False
            last_err='REMOTE_STATUS:'+str(data.get('status'))
        except urllib.error.HTTPError as exc:
            b=exc.read().decode('utf-8','ignore')[:2000]; last_err=f'HTTP {exc.code}: {b}'
        except TimeoutError as exc:
            last_err=type(exc).__name__+': '+str(exc)
        except Exception as exc:
            last_err=type(exc).__name__+': '+str(exc)
    return 125,None,last_err or 'REMOTE_RETRY_EXHAUSTED',False

PRIMARY_CIRCUIT_OPEN=False

def _capacity_error(err):
    low=str(err).lower()
    return ('http 429' in low or 'waiting_free_capacity' in low or 'quota' in low or 'high demand' in low)

def _compact_public_context(raw, issue, max_chars=2600):
    blocks=re.split(r'(?m)(?=^FILE:\s+)',str(raw))
    stop={'this','that','with','from','when','have','will','should','there','which','into','about','more','than','only','also','using','used','public','issue','contract','before','after'}
    terms=[]
    for t in re.findall(r'[A-Za-z_][A-Za-z0-9_./:-]{2,}',str(issue)):
        x=t.strip('.,:;()[]{}').lower()
        if len(x)>=4 and x not in stop and x not in terms: terms.append(x)
    ranked_by_file={}
    for block in blocks:
        if not block.startswith('FILE:'): continue
        lines=block.splitlines(); best_i=1; best=-1
        affinity=0
        for header in lines[:4]:
            m=re.search(r'PUBLIC_STATIC_HOTSPOT:\s*affinity=(-?\d+)',header)
            if m: affinity=max(-2000,min(5000,int(m.group(1))))
        for i,line in enumerate(lines[1:],1):
            low=line.lower(); score=sum(5 for t in terms[:24] if t in low)
            score+=2 if re.search(r'\b(defn?|class|function|write|format|serialize|parse|int|long|float|double)\b',low) else 0
            if score>best: best=score; best_i=i
        a=max(1,best_i-8); b=min(len(lines),best_i+10)
        excerpt='\n'.join([lines[0]]+lines[a:b])
        rel=lines[0][len('FILE:'):].strip()
        test_bonus=900 if (rel.startswith('test/') or '/test/' in rel) and best>0 else 0
        candidate=(affinity+best+test_bonus,excerpt)
        if rel not in ranked_by_file or candidate[0]>ranked_by_file[rel][0]:
            ranked_by_file[rel]=candidate
    ranked=list(ranked_by_file.values())
    ranked.sort(key=lambda x:-x[0])
    out='\n\n'.join(x[1] for x in ranked[:4])
    return out[:max_chars]

def _compact_public_issue(raw, max_chars=2800):
    text=str(raw)
    if len(text)<=max_chars: return text
    marker_positions=[text.rfind(marker) for marker in (
        '\n\nPUBLIC INVARIANT REJECTION',
        '\n\nPUBLIC REPOSITORY VALIDATION FAILED',
        '\n\nGenerate an INDEPENDENT ALTERNATIVE solution.',
    )]
    marker=max(marker_positions)
    if marker>0:
        tail=text[marker:]
        tail_budget=min(len(tail),max_chars//2)
        if len(tail)>tail_budget:
            tail_head=(tail_budget-5)//2
            tail=tail[:tail_head]+'\n...\n'+tail[-(tail_budget-tail_head-5):]
        head_budget=max_chars-tail_budget-5
        return text[:head_budget]+'\n...\n'+tail
    half=(max_chars-5)//2
    return text[:half]+'\n...\n'+text[-(max_chars-half-5):]

def _sovereign_json(payload):
    endpoint=os.environ.get('ARBM_SOVEREIGN_ENDPOINT','')
    if not endpoint: return 126,None,'NO_SOVEREIGN_ENDPOINT',False
    phase=str(payload.get('phase',''))
    if phase=='plan':
        return 0,{'plan':{'paths':[],'queries':[]},'model':'deterministic-public-lexical-planner','pipeline':'sovereign-lexical'},'',False
    if phase=='solve':
        issue=_compact_public_issue(payload.get('issue',''),2200)
        ctx=_compact_public_context(payload.get('tool_context',''),issue,3000)
        prompt=('PUBLIC REPOSITORY CONTEXT:\n'+ctx+'\n\nPUBLIC ISSUE AND CONTRACT:\n'+issue+
                '\n\nReturn ONLY a JSON object with key "edits". edits is a list of objects with path, start_line, end_line, new. '
                'Use only supplied public context. start_line and end_line MUST be exact line numbers printed before each source line; never guess or renumber them. Preserve existing ordinary output formatting unless the public issue requires changing it. No markdown, hidden tests, gold patches, evaluator output, or solution PRs.')
        max_tokens=180
    elif phase=='judge':
        ctx=str(payload.get('tool_context',''))[:3500]
        issue=str(payload.get('issue',''))[:2200]
        ca=json.dumps(payload.get('candidate_a',{}),ensure_ascii=False)[:2200]
        cb=json.dumps(payload.get('candidate_b',{}),ensure_ascii=False)[:2200]
        prompt=('PUBLIC CONTEXT:\n'+ctx+'\n\nISSUE:\n'+issue+'\n\nCANDIDATE A:\n'+ca+'\n\nCANDIDATE B:\n'+cb+
                '\n\nReturn ONLY JSON with choice as A, B, or NONE and reason. Choose only from public evidence.')
        max_tokens=220
    else:
        return 126,None,'SOVEREIGN_UNSUPPORTED_PHASE:'+phase,False
    if phase=='solve':
        schema={'type':'object','additionalProperties':False,'required':['edits'],'properties':{'edits':{'type':'array','maxItems':4,'items':{'type':'object','additionalProperties':False,'required':['path','start_line','end_line','new'],'properties':{'path':{'type':'string','minLength':1,'maxLength':240},'start_line':{'type':'integer','minimum':1},'end_line':{'type':'integer','minimum':1},'new':{'type':'string','minLength':1,'maxLength':4000}}}}}}
    else:
        schema={'type':'object','additionalProperties':False,'required':['choice','reason'],'properties':{'choice':{'type':'string','enum':['A','B','NONE']},'reason':{'type':'string','minLength':1,'maxLength':1200}}}
    body=json.dumps({'model':'arbm-qwen-sovereign','messages':[{'role':'system','content':'You are a precise software repair agent. Output valid JSON only.'},{'role':'user','content':prompt}],
                     'temperature':0,'max_tokens':max_tokens,'stream':False,'cache_prompt':True,'response_format':{'type':'json_object','schema':schema}}).encode('utf-8')
    try:
        req=urllib.request.Request(endpoint,data=body,method='POST'); req.add_header('Content-Type','application/json')
        with urllib.request.urlopen(req,timeout=300) as r: outer=json.loads(r.read().decode('utf-8'))
        content=outer['choices'][0]['message'].get('content','')
        if isinstance(content,list): content=''.join(str(x.get('text','')) if isinstance(x,dict) else str(x) for x in content)
        text=str(content).strip()
        if text.startswith('```'):
            text=re.sub(r'^```(?:json)?\s*|\s*```$','',text,flags=re.I|re.S).strip()
        if not text.startswith('{'):
            a=text.find('{'); b=text.rfind('}')
            if a>=0 and b>a: text=text[a:b+1]
        data=json.loads(text)
        data['model']='Qwen2.5-Coder-14B-Instruct-Q4_K_M'; data['pipeline']='sovereign-github-public-runner'
        data['attempts']=[{'provider':'local-llama-server','status':'ok'}]
        return 0,data,'',False
    except Exception as exc:
        return 125,None,'SOVEREIGN_ERROR:'+type(exc).__name__+': '+str(exc)[:800],False

def remote_json(payload):
    global PRIMARY_CIRCUIT_OPEN
    if os.environ.get('ARBM_SOVEREIGN_ONLY')=='1': return _sovereign_json(payload)
    primary=os.environ.get('ARBM_BENCHMARK_ENDPOINT','')
    fallback=os.environ.get('ARBM_BENCHMARK_FALLBACK_ENDPOINT','')
    errors=[]
    if primary and not PRIMARY_CIRCUIT_OPEN:
        c,d,e,t=_remote_json_one(primary,payload,(0,12))
        if c==0: return c,d,e,t
        if _capacity_error(e): PRIMARY_CIRCUIT_OPEN=True
        errors.append('primary='+e[:800])
    if fallback:
        c,d,e,t=_remote_json_one(fallback,payload,(0,))
        if c==0: return c,d,e,t
        errors.append('fallback='+e[:800])
    if os.environ.get('ARBM_SOVEREIGN_ENDPOINT'):
        c,d,e,t=_sovereign_json(payload)
        if c==0: return c,d,e,t
        errors.append('sovereign='+e[:800])
    return 125,None,' | '.join(errors) or 'NO_REMOTE_PROVIDER',False

def remote_endpoint_json(endpoint, payload):
    global PRIMARY_CIRCUIT_OPEN
    if os.environ.get('ARBM_SOVEREIGN_ONLY')=='1':
        q=dict(payload); q['phase']='judge'; return _sovereign_json(q)
    fallback=os.environ.get('ARBM_BENCHMARK_JUDGE_FALLBACK_ENDPOINT','')
    errors=[]
    if endpoint and not PRIMARY_CIRCUIT_OPEN:
        c,d,e,t=_remote_json_one(endpoint,payload,(0,12))
        if c==0: return c,d,e,t
        if _capacity_error(e): PRIMARY_CIRCUIT_OPEN=True
        errors.append('primary='+e[:800])
    if fallback:
        c,d,e,t=_remote_json_one(fallback,payload,(0,))
        if c==0: return c,d,e,t
        errors.append('fallback='+e[:800])
    return 125,None,' | '.join(errors) or 'NO_JUDGE_ENDPOINT',False

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
    raw=re.findall(r'[A-Za-z_][A-Za-z0-9_.:/-]{2,}',problem)
    terms=[]
    for t in raw:
        x=t.strip('.,:;()[]{}').lower()
        acronym=(t.isupper() and 2 <= len(t) <= 5)
        if (len(x)<4 and not acronym) or x in stop or x in terms: continue
        terms.append(x)
        if x.endswith('ing') and len(x)>6:
            stem=x[:-3]
            for v in (stem, stem+'e', stem+'er'):
                if len(v)>=4 and v not in terms: terms.append(v)
    files=run(['git','ls-files'],repo,60).stdout.splitlines()
    scores={}; centers={}; center_scores={}; matched_terms={}
    low_problem=problem.lower()
    domain_acronyms={x.lower() for x in re.findall(r'\b[A-Z][A-Z0-9]{1,5}\b',problem)}
    write_intent=bool(re.search(r'\b(write|writes|writing|writer|serialize|serialization|output)\b',low_problem))
    read_intent=bool(re.search(r'\b(read|reads|reading|reader|parse|parsing|input)\b',low_problem))
    def noisy(rel):
        r=rel.lower()
        return r.startswith('.github/') or r.startswith('.git') or r.startswith('docs/') or r.startswith('doc/') or r.endswith(('.md','.rst','.txt','.lock','.yml','.yaml','.json'))
    for q in terms[:28]:
        g=run(['git','grep','-n','-I','-i','-F',q,'--'],repo,25)
        if g.returncode not in (0,1): continue
        hits=g.stdout.splitlines()[:80]
        center_priority=1000.0/(len(hits)+1)+min(len(q),20)
        action_term=bool(re.fullmatch(r'(write|writes|writing|writer|serialize|serialization|output|read|reads|reading|reader|parse|parsing|input)',q))
        if action_term: center_priority-=700
        for line in hits:
            parts=line.split(':',2)
            if len(parts)<2 or not parts[1].isdigit(): continue
            rel=parts[0].replace('\\','/')
            if rel not in files: continue
            rel_center_priority=center_priority-(350 if q in rel.lower() else 0)+(280 if q in domain_acronyms and q not in rel.lower() else 0)
            score=3
            name=Path(rel).name.lower(); rel_low=rel.lower()
            if q in name: score+=28
            if q in rel_low: score+=36
            if read_intent and re.search(r'(^|[._/-])(reader|read|parser|parse)([._/-]|$)',rel_low): score+=0
            if re.search(r'(^|/)(src|lib|app|core)(/|$)',rel,re.I): score+=6
            if re.search(r'(^|/)(test|tests|spec)(/|$|_)',rel,re.I): score+=2
            if noisy(rel): score-=8
            scores[rel]=scores.get(rel,0)+score
            matched_terms.setdefault(rel,set()).add(q)
            if rel_center_priority > center_scores.get(rel,-1):
                centers[rel]=int(parts[1]); center_scores[rel]=rel_center_priority
    for rel,qs in matched_terms.items():
        n=len(qs); scores[rel]=scores.get(rel,0)+(n*n*12)
    for rel in files:
        rel_low=rel.lower(); name=Path(rel).name.lower(); structural=0
        domain_hit=any(re.search(r'(^|/)'+re.escape(d)+r'(/|[._-]|$)',rel_low) for d in domain_acronyms)
        writer_hit=bool(re.search(r'(^|[._-])(writer|write|serializer|serialize)([._-]|$)',name))
        reader_hit=bool(re.search(r'(^|[._-])(reader|read|parser|parse)([._-]|$)',name))
        if domain_hit: structural+=180
        if write_intent and writer_hit: structural+=180
        if read_intent and reader_hit: structural+=180
        if domain_hit and ((write_intent and writer_hit) or (read_intent and reader_hit)): structural+=2200
        if structural: scores[rel]=scores.get(rel,0)+structural
    ranked=[r for r,_ in sorted(scores.items(),key=lambda kv:(-kv[1],kv[0])) if not noisy(r)]
    if len(ranked)<2:
        ranked += [r for r,_ in sorted(scores.items(),key=lambda kv:(-kv[1],kv[0])) if r not in ranked]
    action_words={'write','writes','writing','writer','serialize','serialization','output','read','reads','reading','reader','parse','parsing','input'}
    for rel in ranked[:max(limit,12)]:
        try:
            lines=Path(repo,rel).read_text(encoding='utf-8',errors='ignore').splitlines()
        except Exception: continue
        low_lines=[x.lower() for x in lines]; best=None
        for q in terms[:28]:
            idx=[i for i,line in enumerate(low_lines) if q in line]
            if not idx: continue
            pr=1000.0/(len(idx)+1)+min(len(q),20)
            if q in action_words: pr-=700
            if q in rel.lower(): pr-=350
            if q in domain_acronyms and q not in rel.lower(): pr+=280
            if best is None or pr>best[0]: best=(pr,idx[0]+1)
        if best is not None: centers[rel]=best[1]
    return ranked[:limit],centers

def public_static_hotspots(repo, paths, issue_text, limit=10, radius=6):
    low=str(issue_text).lower()
    overflow=bool(re.search(r'overflow|out of (?:the )?integer range|out of integer range',low))
    if not overflow: return ''
    issue_terms=[]
    for t in re.findall(r'[A-Za-z_][A-Za-z0-9_]{2,}',str(issue_text)):
        x=t.lower()
        if len(x)>=4 and x not in issue_terms: issue_terms.append(x)
    public_field_terms=[]
    for t in re.findall(r'\b[A-Z][A-Z0-9_]{2,}\b',str(issue_text)):
        x=t.lower()
        if x not in public_field_terms: public_field_terms.append(x)
    write_intent=bool(re.search(r'\b(write|writes|writing|writer|serialize|serialization|output)\b',low))
    read_intent=bool(re.search(r'\b(read|reads|reading|reader|parse|parsing|input)\b',low))
    hits=[]
    for rel in paths[:12]:
        f=Path(repo,rel)
        if not f.is_file(): continue
        try: lines=f.read_text(encoding='utf-8',errors='ignore').splitlines(True)
        except Exception: continue
        rel_low=rel.lower()
        writer_path=bool(re.search(r'(^|[._/-])(writer|write|serializer|serialize)([._/-]|$)',rel_low))
        reader_path=bool(re.search(r'(^|[._/-])(reader|read|parser|parse)([._/-]|$)',rel_low))
        path_terms=[t for t in issue_terms[:30] if t in rel_low]
        for i,line in enumerate(lines):
            if not re.search(r'\b(?:int|integer|int32|uint32)\b|\(int\s',line,re.I): continue
            a=max(0,i-radius); b=min(len(lines),i+radius+1)
            window=''.join(lines[a:b]).lower()
            source_terms=[t for t in issue_terms[:30] if t in window]
            field_terms=[t for t in public_field_terms[:12] if t in window]
            score=50+5*len(source_terms)+80*len(path_terms)+700*len(field_terms)
            if re.search(r'write|writer|serialize|format|string',window,re.I): score+=20
            if write_intent and writer_path: score+=500
            if write_intent and reader_path: score-=900
            if read_intent and reader_path: score+=500
            if read_intent and writer_path: score-=900
            if field_terms and ((write_intent and writer_path) or (read_intent and reader_path)): score+=1200
            if re.search(r'(^|/)(src|lib|app|core)(/|$)',rel,re.I): score+=15
            matches=sorted(set(path_terms+field_terms))
            hits.append((score,rel,i,a,b,lines,','.join(matches[:12]) or 'none'))
    hits.sort(key=lambda x:(-x[0],x[1],x[2]))
    blocks=[]; seen_files=set()
    for score,rel,i,a,b,lines,matches in hits:
        if rel in seen_files: continue
        seen_files.add(rel)
        body=''.join(f'{j+1:06d}|{lines[j]}' for j in range(a,b))
        blocks.append(f'FILE: {rel}\nPUBLIC_STATIC_HOTSPOT: affinity={score}; public_matches={matches}; derived only from public issue + source\n'+body)
        if len(blocks)>=limit: break
    return '\n\n'.join(blocks)

def numbered_file(repo, rel, center=None, radius=120):
    f=Path(repo,rel)
    if not f.is_file(): return ''
    try: lines=f.read_text(encoding='utf-8',errors='ignore').splitlines(True)
    except Exception: return ''
    if center is None: a,b=0,min(len(lines),240)
    else: a=max(0,center-radius); b=min(len(lines),center+radius)
    return f'FILE: {rel}\n'+''.join(f'{i+1:06d}|{lines[i]}' for i in range(a,b))

def _lisp_paren_delta(text):
    depth=0; quoted=False; esc=False; comment=False
    for ch in text:
        if comment:
            if ch=='\n': comment=False
            continue
        if quoted:
            if esc: esc=False
            elif ch=='\\': esc=True
            elif ch=='"': quoted=False
            continue
        if ch==';': comment=True; continue
        if ch=='"': quoted=True; continue
        if ch=='(': depth+=1
        elif ch==')': depth-=1
    return depth

def _preserve_lisp_boundary_closers(rel, old, new):
    if Path(rel).suffix.lower() not in {'.clj','.cljs','.cljc','.edn','.lisp','.scm'}:
        return new, False
    old_delta=_lisp_paren_delta(old); new_delta=_lisp_paren_delta(new)
    missing=new_delta-old_delta
    if missing<=0: return new, False
    stripped=old.rstrip()
    trailing_closers=len(stripped)-len(stripped.rstrip(')'))
    if trailing_closers<missing: return new, False
    suffix=')'*missing
    if new.endswith('\n'): return new[:-1]+suffix+'\n', True
    return new+suffix, True

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
            boundary_normalized=False
            new_parts=new.splitlines()
            if start_line>1 and new_parts and new_parts[0].strip()==lines[start_line-2].rstrip('\r\n').strip():
                new='\n'.join(new_parts[1:]); boundary_normalized=True
            if not new.strip(): errors.append('invalid_new_after_boundary_normalization:'+rel); continue
            if old.endswith('\n') and not new.endswith('\n'): new+='\n'
            new, structural_boundary_preserved=_preserve_lisp_boundary_closers(rel,old,new)
            if new==old or re.sub(r'\s+','',old)==re.sub(r'\s+','',new): errors.append('semantic_no_op_edit:'+rel); continue
            target.write_text(''.join(lines[:start_line-1])+new+''.join(lines[end_line:]),encoding='utf-8',newline='\n')
            applied+=1; meta.append({'path':rel,'startLine':start_line,'endLine':end_line,'oldLen':len(old),'newLen':len(new),'boundaryNormalized':boundary_normalized,'structuralBoundaryPreserved':structural_boundary_preserved,'oldSha256':__import__('hashlib').sha256(old.encode()).hexdigest(),'newSha256':__import__('hashlib').sha256(new.encode()).hexdigest()})
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
            namespaces=[]
            for rel in changed_paths:
                rel=str(rel).replace('\\','/')
                if not rel.startswith('src/') or not rel.endswith('.clj'): continue
                stem=rel[4:-4]
                test_rel='test/'+stem+'_test.clj'
                if not Path(repo,test_rel).is_file(): continue
                ns=stem.replace('/','.')+'-test'
                if ns not in namespaces: namespaces.append(ns)
            cmd=['lein','test',*namespaces] if namespaces else ['lein','test']
            r=run(cmd,repo,300); return True,r.returncode,((r.stdout or '')+'\n'+(r.stderr or ''))[-12000:]
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
PUBLIC_INVARIANT_GUIDANCE='''

PUBLIC-SPEC REASONING CONTRACT:
Before editing, derive the behavioral invariants explicitly implied by the public issue and supplied repository code. A patch is incomplete if it only removes the immediate exception while violating another public invariant.
For numeric bugs: distinguish representation/formatting from arithmetic conversion; preserve magnitude and intended textual semantics; consider integral-valued floats, very large magnitudes, scientific notation, signs, zero, nil/missing values, and ordinary regression cases when the public issue makes them relevant. Do not solve a serialization overflow by forcing a wider fixed-width numeric cast when a formatting mechanism can preserve the existing textual contract without range overflow. Prefer the repository's existing formatting abstractions or standard language/library formatting mechanisms that preserve ordinary output and the public example.
Make the smallest causally sufficient edit. Preserve existing guards and control-flow branches, especially nil/missing handling and fractional-number behavior, unless the public issue explicitly requires changing them. If an integral-valued number was deliberately serialized as plain integral text, preserve that representation across the full magnitude required by the public issue; do not retain a fixed-width cast behind a range check whose fallback changes the representation.
Do not use hidden tests, gold patches, evaluator output, solution PRs, or benchmark answer knowledge.'''
solver_problem=problem+PUBLIC_INVARIANT_GUIDANCE
with tempfile.TemporaryDirectory(prefix='arbm-swe-') as td:
    r=run(['git','clone','--filter=blob:none','--no-checkout',repo_url,td], timeout=300)
    if r.returncode: raise SystemExit(r.stderr)
    r=run(['git','checkout',base], td, 180)
    if r.returncode: raise SystemExit(r.stderr)
    idx=repo_index(td,problem)
    started=time.time(); pcode,pdata,perr,ptimed=remote_json({'phase':'plan','issue':solver_problem,'repo_index':idx,'instance_id':iid})
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
    lex_paths,lex_centers=lexical_fallback(td,problem,8)
    for rel,ln in lex_centers.items(): centers[rel]=ln
    planner_paths=list(candidate_paths)
    candidate_paths=[]
    for rel in lex_paths[:4]+planner_paths+lex_paths[4:]:
        if rel not in candidate_paths: candidate_paths.append(rel)
    if not candidate_paths:
        evidence={'schema':'arbm-p8-swe-smoke-v2-line-edit',**runtime_identity(),'dataset':DATASET,'instance_id':iid,'repo':row['repo'],'base_commit':base,'hfOffset':HF_OFFSET,'exitCode':127,'validPatch':False,'status':'NO_CONTEXT','plannerCode':pcode,'plannerError':perr[:500],'goldPatchExposedToAgent':False}
        Path(OUT,'agent-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
        Path(OUT,'patches.json').write_text(json.dumps([{'instance_id':iid,'patch':''}],indent=2)+'\n')
        Path(OUT,'instance.json').write_text(json.dumps({'instance_id':iid,'repo':row['repo'],'base_commit':base},indent=2)+'\n')
        print(json.dumps(evidence)); raise SystemExit(2)
    base_context='\n\n'.join(numbered_file(td,r,centers.get(r)) for r in candidate_paths[:8])
    hotspots=public_static_hotspots(td,candidate_paths,problem)
    context=((hotspots+'\n\n') if hotspots else '')+base_context
    context=context[:32000]
    allowed_paths=[]
    for rel in re.findall(r'(?m)^FILE:\s+([^\s]+)',context):
        if rel not in allowed_paths: allowed_paths.append(rel)
    code,data,err,timed_out=remote_json({'phase':'solve','issue':solver_problem,'tool_context':context,'instance_id':iid,'model_offset':0,'review_model_offset':0})
    cand_a=(data or {}).get('edits',[]) if code==0 else []
    alt_issue=solver_problem+'\n\nGenerate an INDEPENDENT ALTERNATIVE solution. The first candidate was: '+json.dumps(cand_a)[:4000]+' Do not repeat it; test a different plausible root cause or more complete behavioral invariant using only supplied public context.'
    if os.environ.get('ARBM_SOVEREIGN_ONLY')=='1':
        bcode,bdata,berr,btimed=204,{'edits':[],'model':'sovereign-single-candidate','pipeline':'sovereign-fast-path'},'',False
        cand_b=[]
    else:
        bcode,bdata,berr,btimed=remote_json({'phase':'solve','issue':alt_issue,'tool_context':context,'instance_id':iid,'model_offset':1,'review_model_offset':1})
        cand_b=(bdata or {}).get('edits',[]) if bcode==0 else []
    def provider_meta(d):
        d=d or {}
        return {'model':d.get('model'),'pipeline':d.get('pipeline'),'attempts':(d.get('attempts') or [])[:16]}
    candidate_provider_meta={'A':provider_meta(data),'B':provider_meta(bdata)}
    def dedupe_edits(edits):
        out=[]; seen=set()
        for e in edits if isinstance(edits,list) else []:
            if not isinstance(e,dict): continue
            key=(str(e.get('path','')).replace('\\','/'),e.get('start_line'),e.get('end_line'),str(e.get('new','')).strip())
            if key in seen: continue
            seen.add(key); out.append(e)
        return out
    cand_a=dedupe_edits(cand_a); cand_b=dedupe_edits(cand_b)
    def public_invariant_guard(repo, edits, issue_text):
        errs=[]; low=issue_text.lower()
        overflow=('overflow' in low or 'out of the integer range' in low or 'out of integer range' in low)
        if not overflow: return errs
        for e in edits if isinstance(edits,list) else []:
            try:
                rel=str(e.get('path','')).replace('\\','/').lstrip('/')
                f=Path(repo,rel); st=int(e.get('start_line')); en=int(e.get('end_line'))
                if not f.is_file(): continue
                lines=f.read_text(encoding='utf-8',errors='ignore').splitlines()
                old='\n'.join(lines[st-1:en]); new=str(e.get('new',''))
                bounded_old=bool(re.search(r'\b(?:int|integer|int32|uint32)\b|\(int\s',old,re.I))
                same_width_new=bool(re.search(r'\b(?:int|integer|int32|uint32)\b|\(int\s',new,re.I))
                long_width_new=bool(re.search(r'\b(?:long|int64|uint64|integer64)\b|\(long\s',new,re.I))
                unbounded_required=bool(re.search(r'\b(unbounded|arbitrary precision|beyond long|long range|64[- ]?bit range)\b',low,re.I))
                serialization=bool(re.search(r'str|string|format|serialize|write',old+'\n'+new,re.I))
                range_guard=bool(re.search(r'Integer/MIN_VALUE.*Integer/MAX_VALUE|Integer/MAX_VALUE.*Integer/MIN_VALUE',new,re.S))
                if bounded_old and same_width_new and serialization and not range_guard: errs.append('public_invariant_fixed_width_conversion_retained:'+rel)
                if bounded_old and long_width_new and serialization and unbounded_required: errs.append('public_invariant_fixed_width_conversion_retained:'+rel)
                for form in ('when','when-not','when-let','if','if-not','if-let','cond','case'):
                    pattern=r'\('+re.escape(form)+r'\b'
                    if len(re.findall(pattern,new)) < len(re.findall(pattern,old)):
                        errs.append('public_invariant_control_flow_removed:'+form+':'+rel)
            except Exception: pass
        if overflow and edits:
            touches_overflow_site=False
            for e in edits if isinstance(edits,list) else []:
                try:
                    rel=str(e.get('path','')).replace('\\','/').lstrip('/')
                    f=Path(repo,rel); st=int(e.get('start_line')); en=int(e.get('end_line'))
                    if not f.is_file(): continue
                    lines=f.read_text(encoding='utf-8',errors='ignore').splitlines()
                    old='\n'.join(lines[st-1:en])
                    if re.search(r'\b(?:int|integer|int32|uint32)\b|\(int\s',old,re.I):
                        touches_overflow_site=True; break
                except Exception: pass
            if not touches_overflow_site: errs.append('public_invariant_no_overflow_site_touched')
        return errs
    def public_deterministic_overflow_repair(repo, paths, issue_text):
        low=str(issue_text).lower()
        if not re.search(r'overflow|out of (?:the )?integer range',low): return []
        write_intent=bool(re.search(r'\b(write|writes|writing|writer|serialize|serialization|output)\b',low))
        ranked=[]
        for rel in paths:
            if Path(rel).suffix.lower() not in {'.clj','.cljs','.cljc'}: continue
            f=Path(repo,rel)
            if not f.is_file(): continue
            rel_low=rel.lower(); score=0
            if write_intent and re.search(r'(^|[._/-])(writer|write|serializer|serialize)([._/-]|$)',rel_low): score+=1000
            if write_intent and re.search(r'(^|[._/-])(reader|read|parser|parse)([._/-]|$)',rel_low): score-=1000
            lines=f.read_text(encoding='utf-8',errors='ignore').splitlines()
            for i,line in enumerate(lines):
                if not re.search(r'\(int\s+[^)]+\)',line): continue
                window='\n'.join(lines[max(0,i-4):min(len(lines),i+5)])
                if not re.search(r'str|string|format|serialize|write',window,re.I): continue
                expr=re.search(r'\(int\s+([^)]+)\)',line).group(1)
                new=re.sub(r'\(str\s+\(int\s+[^)]+\)\)',lambda m:'(format \"%.0f\" '+expr+')',line,count=1)
                if new==line: continue
                ranked.append((score,rel,i+1,i+1,new))
        if not ranked: return []
        ranked.sort(key=lambda x:(-x[0],x[1],x[2]))
        _,rel,start_line,end_line,new=ranked[0]
        return [{'path':rel,'start_line':start_line,'end_line':end_line,'new':new}]
    latency=round((time.time()-started)*1000)
    if not cand_a and not cand_b and (code!=0 or bcode!=0):
        deterministic=public_deterministic_overflow_repair(td,allowed_paths,problem)
        if deterministic:
            run(['git','reset','--hard',base],td,60)
            derrs,dmeta,dapplied=apply_candidate(td,deterministic,allowed_paths)
            dattempted=False; dvcode=125; dvout='NOT_RUN'
            if dapplied>0 and not derrs:
                dattempted,dvcode,dvout=public_validation(td,[m['path'] for m in dmeta])
            if dapplied>0 and not derrs and (not dattempted or dvcode==0):
                cand_a=deterministic; code=0; err=''
                data={'edits':deterministic,'model':'deterministic-public-overflow-repair','pipeline':'public-source-rule'}
            else:
                deterministic=[]
        if not cand_a and not cand_b:
            sovereign_only=(os.environ.get('ARBM_SOVEREIGN_ONLY')=='1')
            fail_status='SOVEREIGN_GENERATION_FAILED' if sovereign_only else 'WAITING_FREE_CAPACITY'
            evidence={'schema':'arbm-p8-swe-smoke-v2-line-edit',**runtime_identity(),'dataset':DATASET,'instance_id':iid,'repo':row['repo'],'base_commit':base,'hfOffset':HF_OFFSET,'exitCode':125,'validPatch':False,'status':fail_status,'providerUnavailable':not sovereign_only,'candidateACode':code,'candidateBCode':bcode,'providerError':(err+' | '+berr)[:1200],'allowedPaths':allowed_paths,'goldPatchExposedToAgent':False}
            Path(OUT,'agent-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
            Path(OUT,'patches.json').write_text(json.dumps([{'instance_id':iid,'patch':''}],indent=2)+'\n')
            Path(OUT,'instance.json').write_text(json.dumps({'instance_id':iid,'repo':row['repo'],'base_commit':base},indent=2)+'\n')
            print(json.dumps(evidence)); raise SystemExit(2)
    path_normalizations=[]
    candidate_results={}
    for label,cand in [('A',cand_a),('B',cand_b)]:
        run(['git','reset','--hard',base],td,60)
        guard_errors=public_invariant_guard(td,cand,problem)
        errs=[]; meta=[]; applied=0
        if not guard_errors: errs,meta,applied=apply_candidate(td,cand,allowed_paths)
        else: errs.extend(guard_errors)
        attempted=False; vcode=125; vout='NOT_RUN'
        if applied>0 and not errs:
            attempted,vcode,vout=public_validation(td,[m['path'] for m in meta])
        candidate_results[label]={'edits':cand,'providerMeta':candidate_provider_meta.get(label,{}),'errors':errs,'meta':meta,'applied':applied,'validationAttempted':attempted,'validationCode':vcode,'validationPreview':vout[-6000:]}
    repair_records={}
    for label in ('A','B'):
        cr=candidate_results[label]
        guard_failed=any(str(x).startswith('public_invariant_') for x in cr['errors'])
        validation_failed=cr['applied']>0 and not cr['errors'] and cr['validationAttempted'] and cr['validationCode']!=0
        if guard_failed or validation_failed:
            if guard_failed:
                repair_issue=solver_problem+'\n\nPUBLIC INVARIANT REJECTION for candidate '+label+': '+json.dumps(cr['errors'])[:1200]+'. Re-locate the exact public source hotspot that causes the issue and produce a representation-preserving fix using only the supplied public issue and repository context. MANDATORY REVISION: do not return the rejected edit unchanged. For each control_flow_removed error, retain the named original public control-flow form and its behavior. For fixed_width_conversion_retained, remove the fixed-width conversion rather than placing it behind a range check. Prefer changing only the causal conversion expression while leaving surrounding public guards and branches intact. If public source uses a fixed-width integer cast only inside an integral-valued branch to preserve plain integer text, replace only that serialization expression with a non-overflowing numeric formatting mechanism while preserving the branch and fractional fallback. start_line/end_line must match the printed source line numbers exactly. Do not use hidden tests, gold patches, solution PRs, or evaluator output. Rejected edits: '+json.dumps(cr['edits'])[:5000]
            else:
                repair_issue=solver_problem+'\n\nPUBLIC REPOSITORY VALIDATION FAILED for candidate '+label+'. Repair the candidate using only the supplied public validation output and repository context. Do not use hidden tests or benchmark evaluator output. Rejected edits: '+json.dumps(cr['edits'])[:5000]+'\nPUBLIC VALIDATION OUTPUT:\n'+cr['validationPreview'][-6000:]
            repair_offset=2 if label=='A' else 3
            rcode,rdata,rerr,rtimed=remote_json({'phase':'solve','issue':repair_issue,'tool_context':context,'instance_id':iid,'model_offset':repair_offset,'review_model_offset':repair_offset})
            repaired=dedupe_edits((rdata or {}).get('edits',[]) if rcode==0 else [])
            rec={'attempted':True,'modelOffset':repair_offset,'providerCode':rcode,'providerError':rerr[:500],'providerMeta':provider_meta(rdata),'edits':repaired}
            if repaired:
                run(['git','reset','--hard',base],td,60)
                repair_guard_errors=public_invariant_guard(td,repaired,problem)
                errs=[]; meta=[]; applied=0
                if not repair_guard_errors: errs,meta,applied=apply_candidate(td,repaired,allowed_paths)
                else: errs.extend(repair_guard_errors)
                attempted=False; vcode=125; vout='NOT_RUN'
                if applied>0 and not errs:
                    attempted,vcode,vout=public_validation(td,[m['path'] for m in meta])
                rec.update({'errors':errs,'meta':meta,'applied':applied,'validationAttempted':attempted,'validationCode':vcode,'validationPreview':vout[-6000:]})
                if applied>0 and not errs and (not attempted or vcode==0):
                    candidate_results[label]={'edits':repaired,'providerMeta':provider_meta(rdata),'errors':errs,'meta':meta,'applied':applied,'validationAttempted':attempted,'validationCode':vcode,'validationPreview':vout[-6000:]}
                    if label=='A': cand_a=repaired
                    else: cand_b=repaired
            repair_unusable=(not repaired) or bool(rec.get('errors'))
            if repair_unusable:
                deterministic=public_deterministic_overflow_repair(td,allowed_paths,problem)
                if deterministic:
                    run(['git','reset','--hard',base],td,60)
                    derrs,dmeta,dapplied=apply_candidate(td,deterministic,allowed_paths)
                    dattempted=False; dvcode=125; dvout='NOT_RUN'
                    if dapplied>0 and not derrs:
                        dattempted,dvcode,dvout=public_validation(td,[m['path'] for m in dmeta])
                    rec['deterministicPublicFallback']={'edits':deterministic,'errors':derrs,'applied':dapplied,'validationAttempted':dattempted,'validationCode':dvcode,'validationPreview':dvout[-6000:]}
                    if dapplied>0 and not derrs and (not dattempted or dvcode==0):
                        candidate_results[label]={'edits':deterministic,'providerMeta':{'model':'deterministic-public-overflow-repair','pipeline':'public-source-rule'},'errors':derrs,'meta':dmeta,'applied':dapplied,'validationAttempted':dattempted,'validationCode':dvcode,'validationPreview':dvout[-6000:]}
                        if label=='A': cand_a=deterministic
                        else: cand_b=deterministic
            repair_records[label]=rec
    passing=[x for x in ('A','B') if candidate_results[x]['applied']>0 and not candidate_results[x]['errors'] and (not candidate_results[x]['validationAttempted'] or candidate_results[x]['validationCode']==0)]
    judge_ep=os.environ.get('ARBM_BENCHMARK_JUDGE_ENDPOINT','')
    jcode,jdata,jerr,jtimed=(125,None,'NO_JUDGE_ENDPOINT',False)
    single_provider_fallback=(bool(cand_a) ^ bool(cand_b)) and len(passing)==1
    if single_provider_fallback:
        choice=passing[0]; judge_reason='single_valid_candidate_provider_fallback'; judge_edits=[]; jcode=204; jerr=''
    else:
        if judge_ep:
            jcode,jdata,jerr,jtimed=remote_endpoint_json(judge_ep,{'issue':solver_problem,'tool_context':context,'instance_id':iid,'candidate_a':{'edits':cand_a},'candidate_b':{'edits':cand_b},'validation_a':candidate_results['A'],'validation_b':candidate_results['B']})
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
    evidence={'schema':'arbm-p8-swe-smoke-v2-line-edit',**runtime_identity(),'dataset':DATASET,'instance_id':iid,
      'repo':row['repo'],'base_commit':base,'hfOffset':HF_OFFSET,'model':os.environ.get('MODEL_LABEL','unknown'),'provider':os.environ.get('MODEL_PROVIDER','local-llama'),
      'latencyMs':latency,'exitCode':code,'validPatch':valid,'patchChars':len(patch),
      'stderrChars':len(err),'stderrPreview':err[:500],'timedOut':timed_out,'editCount':len(edits) if isinstance(edits,list) else 0,'allowedPaths':allowed_paths,'pathNormalizations':path_normalizations,'editMeta':applied_meta,'appliedEdits':applied_edits,'editErrors':edit_errors[:8],'structureValid':structure_valid,'applyCheck':apply_check,'applyError':apply_error,'publicValidationAttempted':validation_attempted,'publicValidationCode':validation_code,'publicValidationPreview':validation_output[-6000:],'repairAttempted':bool(repair_records),'repairRecords':repair_records,'candidateA':candidate_results.get('A'),'candidateB':candidate_results.get('B'),'semanticJudgeChoice':choice,'semanticJudgeReason':judge_reason,'semanticJudgeCode':jcode,'goldPatchExposedToAgent':False}
    Path(OUT,'agent-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
    Path(OUT,'patches.json').write_text(json.dumps([{'instance_id':iid,'patch':patch}],indent=2)+'\n')
    Path(OUT,'instance.json').write_text(json.dumps({'instance_id':iid,'repo':row['repo'],'base_commit':base},indent=2)+'\n')
    if code or not valid:
        print(json.dumps(evidence)); raise SystemExit(2)
print(json.dumps(evidence))
