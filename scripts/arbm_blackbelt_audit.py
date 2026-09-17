#!/usr/bin/env python3
import argparse, ast, hashlib, json, os, re, subprocess, tempfile
from collections import Counter, defaultdict
from pathlib import Path

TEXT_EXTS={'.py','.js','.mjs','.cjs','.ts','.tsx','.json','.yml','.yaml','.md','.txt','.toml','.ini','.cfg','.conf','.sh','.ps1','.sql','.patch','.xml','.html','.css'}
SECRET_RE=re.compile(r'(?i)(password|passwd|secret|api[_-]?key|access[_-]?token|private[_-]?key)\s*[:=]\s*["\']([^"\']{8,})["\']')
URL_RE=re.compile(r'https?://[^\s"\'<>]+')
SENSITIVE=re.compile(r'(?i)(password|passwd|secret|token|api[_-]?key|authorization|cookie|private[_-]?key)')

def git(*args):
    return subprocess.check_output(['git',*args], text=True, stderr=subprocess.STDOUT)

def show(sha,path):
    return subprocess.check_output(['git','show',f'{sha}:{path}'], stderr=subprocess.STDOUT)

def add(findings, severity, category, path, line, rule, impact, before, after):
    findings.append({'severity':severity,'category':category,'path':path,'line':line,'rule':rule,'impact':impact,'before':before.rstrip(),'after':after.rstrip()})

def line_rule_scan(path, lines, findings):
    joined='\n'.join(lines)
    is_workflow=path.startswith('.github/workflows/') and Path(path).suffix in {'.yml','.yaml'}
    if is_workflow:
        if not re.search(r'(?m)^permissions:\s*$',joined):
            add(findings,'HIGH','INFRA',path,1,'GH-ACTIONS-PERMISSIONS','Workflow sem permissions globais explícitas herda permissões do repositório; amplia blast radius de token comprometido.','(permissions ausente)','permissions:\n  contents: read')
        if 'concurrency:' not in joined:
            add(findings,'MEDIUM','INFRA',path,1,'GH-ACTIONS-CONCURRENCY','Execuções duplicadas podem consumir capacidade FREE e competir por runners, agravando PROVIDER_CAPACITY_EXHAUSTED.','(concurrency ausente)',"concurrency:\n  group: ${ { github.workflow } }-${ { github.ref } }\n  cancel-in-progress: true".replace('${ {','${{').replace('} }','}}'))
        for i,l in enumerate(lines,1):
            s=l.strip()
            m=re.search(r'uses:\s*([^\s]+)@([^\s#]+)',l)
            if m and not re.fullmatch(r'[0-9a-fA-F]{40}',m.group(2)):
                add(findings,'MEDIUM','SUPPLY_CHAIN',path,i,'UNPINNED-ACTION','Action referenciada por tag/branch mutável; comprometimento upstream pode alterar CI sem mudança no SHA auditado.',s,f"uses: {m.group(1)}@<40-char-commit-sha>")
            if re.search(r'\bcurl\b.*\|\s*(bash|sh)\b',l):
                add(findings,'CRITICAL','SUPPLY_CHAIN',path,i,'CURL-PIPE-SHELL','Executa conteúdo remoto sem verificação criptográfica; permite RCE se origem/DNS/CDN for comprometida.',s,'curl -fsSLo tool.tgz "$URL"\necho "$SHA256  tool.tgz" | sha256sum -c -\ntar -xf tool.tgz')
            if 'docker run' in l:
                miss=[x for x in ['--memory','--cpus','--pids-limit'] if x not in l]
                if miss:
                    add(findings,'HIGH','INFRA',path,i,'DOCKER-NO-LIMITS',f"Container sem {', '.join(miss)} pode exaurir memória/CPU/PIDs do runner e provocar falhas sistêmicas.",s,s+' --memory=4g --cpus=2 --pids-limit=512')
                if '--privileged' in l:
                    add(findings,'CRITICAL','SECURITY',path,i,'DOCKER-PRIVILEGED','Container privilegiado quebra isolamento do runner e expande impacto de código não confiável.',s,s.replace('--privileged','--cap-drop=ALL --security-opt=no-new-privileges'))
            if re.search(r'(?i)echo\s+.*\$\{?[^} ]*(token|secret|password|key)',l):
                add(findings,'CRITICAL','LOGGING',path,i,'SECRET-ECHO','Segredo pode ser gravado em log de CI/artifact.',s,'echo "credential present: ${CREDENTIAL:+yes}"')
            if re.search(r'pip\s+install\s+',l) and not re.search(r'==|requirements',l):
                add(findings,'MEDIUM','SUPPLY_CHAIN',path,i,'UNPINNED-PIP','Dependência instalada sem versão fixa torna execução não reprodutível e vulnerável a regressão/supply-chain.',s,'python -m pip install -r requirements.lock.txt --require-hashes')
    for i,l in enumerate(lines,1):
        s=l.strip()
        sm=SECRET_RE.search(l)
        if sm and not re.search(r'(?i)(example|dummy|placeholder|changeme|test|mock)',sm.group(2)):
            add(findings,'CRITICAL','SECURITY',path,i,'HARDCODED-SECRET','Credencial aparentemente literal no repositório pode permitir acesso não autorizado e exige rotação.',s,f'{sm.group(1).upper()} = os.environ["{sm.group(1).upper()}"]')
        if re.search(r'http://(?!127\.0\.0\.1|localhost|0\.0\.0\.0)',l):
            add(findings,'HIGH','CRYPTO',path,i,'PLAINTEXT-HTTP','Tráfego externo em HTTP é interceptável e modificável em trânsito.',s,s.replace('http://','https://'))
        if re.search(r'(?i)(verify\s*=\s*False|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*["\']?0)',l):
            add(findings,'CRITICAL','CRYPTO',path,i,'TLS-VERIFY-DISABLED','Desabilitar validação TLS permite MITM e invalida autenticidade do endpoint.',s,s.replace('verify=False','verify=True').replace('NODE_TLS_REJECT_UNAUTHORIZED=0','NODE_TLS_REJECT_UNAUTHORIZED=1'))
        if re.search(r'(?i)hashlib\.(md5|sha1)\(',l):
            add(findings,'HIGH','CRYPTO',path,i,'WEAK-HASH','MD5/SHA-1 não devem proteger integridade adversarial ou credenciais.',s,re.sub(r'hashlib\.(md5|sha1)', 'hashlib.sha256', s, flags=re.I))
        if re.search(r'(?i)(console\.log|print\(|logging\.(debug|info|warning|error)).*(token|secret|password|api[_-]?key|authorization)',l):
            add(findings,'HIGH','LOGGING',path,i,'SENSITIVE-LOG','Possível exposição de credenciais/PII em stdout ou logs persistentes.',s,'logger.info("credential_state", extra={"present": bool(credential)})')
        if re.search(r'Access-Control-Allow-Origin["\']?\s*[:,=]\s*["\']\*',l,re.I):
            add(findings,'HIGH','SECURITY',path,i,'CORS-WILDCARD','CORS permissivo permite leitura por qualquer origem quando combinado com endpoints sensíveis.',s,'"Access-Control-Allow-Origin": ALLOWED_ORIGIN')
        if re.search(r'\b(eval|exec)\s*\(',l) and Path(path).suffix in {'.py','.js','.mjs','.ts','.tsx'}:
            add(findings,'CRITICAL','CODE',path,i,'DYNAMIC-EXEC','Execução dinâmica aumenta superfície de code injection se qualquer entrada for controlável externamente.',s,'# Remover eval/exec; usar parser/dispatch explícito com allowlist')
        if re.search(r'\b(shell\s*=\s*True|os\.system\s*\()',l):
            add(findings,'CRITICAL','SECURITY',path,i,'COMMAND-INJECTION','Shell parsing transforma dados em sintaxe de comando e amplia risco de command injection.',s,'subprocess.run([binary, arg1, arg2], check=True, timeout=60, shell=False)')
        if re.search(r'\b(tempfile\.mktemp)\s*\(',l):
            add(findings,'HIGH','SECURITY',path,i,'INSECURE-TEMP','mktemp possui janela de corrida e pode permitir substituição/symlink attack.',s,'with tempfile.NamedTemporaryFile(delete=False) as tmp: ...')
        if re.search(r'\b(pickle\.loads?|yaml\.load)\s*\(',l):
            add(findings,'HIGH','SECURITY',path,i,'UNSAFE-DESERIALIZATION','Desserialização insegura pode executar código ou construir objetos inesperados.',s,s.replace('yaml.load(','yaml.safe_load(').replace('pickle.loads(','json.loads(').replace('pickle.load(','json.load('))

def python_scan(path, text, findings):
    try: tree=ast.parse(text)
    except SyntaxError as e:
        add(findings,'HIGH','CODE',path,e.lineno or 1,'PY-SYNTAX','Arquivo Python não parseia; qualquer caminho que o importe falhará em runtime.',e.text or '(syntax error)','# Corrigir sintaxe e validar com python -m compileall')
        return
    lines=text.splitlines()
    for n in ast.walk(tree):
        if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            end=getattr(n,'end_lineno',n.lineno); span=end-n.lineno+1
            branches=sum(isinstance(x,(ast.If,ast.For,ast.While,ast.Try,ast.BoolOp,ast.Match)) for x in ast.walk(n))
            if span>100 or branches>18:
                add(findings,'MEDIUM','CODE',path,n.lineno,'HIGH-COMPLEXITY',f'Função {n.name} tem {span} linhas e {branches} pontos de decisão; eleva risco de regressão e dificulta teste isolado.',lines[n.lineno-1] if n.lineno<=len(lines) else n.name,f'# Extrair etapas de {n.name} em funções puras menores; meta <80 linhas e complexidade <15')
            for d in n.args.defaults+n.args.kw_defaults:
                if isinstance(d,(ast.List,ast.Dict,ast.Set)):
                    add(findings,'HIGH','CODE',path,n.lineno,'MUTABLE-DEFAULT','Default mutável é compartilhado entre chamadas e causa estado fantasma/memory retention.',lines[n.lineno-1],f'def {n.name}(..., value=None):\n    if value is None: value = []')
        if isinstance(n,ast.ExceptHandler):
            if n.type is None:
                add(findings,'HIGH','CODE',path,n.lineno,'BARE-EXCEPT','Captura BaseException inclusive cancelamento/SystemExit, mascarando falhas e quebrando fail-closed.',lines[n.lineno-1],'except Exception as exc:\n    logger.exception("operation_failed")\n    raise')
            elif isinstance(n.type,ast.Name) and n.type.id=='Exception' and len(n.body)==1 and isinstance(n.body[0],(ast.Pass,ast.Continue)):
                add(findings,'HIGH','CODE',path,n.lineno,'SWALLOWED-EXCEPTION','Exceção genérica é descartada sem telemetria; produz falso sucesso e perda forense.',lines[n.lineno-1],'except Exception as exc:\n    logger.exception("operation_failed")\n    raise')
        if isinstance(n,ast.Call):
            fn=''
            if isinstance(n.func,ast.Attribute): fn=(getattr(n.func.value,'id','')+'.'+n.func.attr).strip('.')
            elif isinstance(n.func,ast.Name): fn=n.func.id
            if fn in {'requests.get','requests.post','requests.put','requests.patch','requests.delete','requests.request','urllib.request.urlopen'}:
                if not any(k.arg=='timeout' for k in n.keywords):
                    add(findings,'HIGH','RELIABILITY',path,n.lineno,'HTTP-NO-TIMEOUT','Chamada de rede sem timeout pode bloquear worker indefinidamente e consumir capacidade até esgotar runners/providers.',lines[n.lineno-1],lines[n.lineno-1].rstrip(')')+', timeout=30)')
            if fn.startswith('subprocess.') and fn not in {'subprocess.list2cmdline'}:
                if not any(k.arg=='timeout' for k in n.keywords) and fn.split('.')[-1] in {'run','call','check_call','check_output'}:
                    add(findings,'MEDIUM','RELIABILITY',path,n.lineno,'SUBPROCESS-NO-TIMEOUT','Subprocesso sem deadline pode travar lane e impedir recovery determinístico.',lines[n.lineno-1],lines[n.lineno-1].rstrip(')')+', timeout=120)')
        if isinstance(n,ast.While) and isinstance(n.test,ast.Constant) and n.test.value is True:
            if not any(isinstance(x,ast.Break) for x in ast.walk(n)):
                add(findings,'HIGH','RELIABILITY',path,n.lineno,'UNBOUNDED-LOOP','Loop infinito sem break explícito depende de exceção/process kill; risco de CPU leak ou lane nunca concluída.',lines[n.lineno-1],'for attempt in range(MAX_ATTEMPTS):\n    ...\nelse:\n    raise RuntimeError("retry_budget_exhausted")')

def js_scan(path, lines, findings):
    for i,l in enumerate(lines,1):
        s=l.strip()
        if re.search(r'\bMath\.random\(\)',l) and re.search(r'(?i)(token|nonce|secret|key|id)',l):
            add(findings,'HIGH','CRYPTO',path,i,'WEAK-RANDOM','Math.random não é CSPRNG para nonce/token/identificador de segurança.',s,"const token = crypto.randomUUID();")
        if re.search(r'\bfetch\s*\(',l) and 'signal:' not in l:
            add(findings,'MEDIUM','RELIABILITY',path,i,'FETCH-NO-DEADLINE','fetch sem AbortSignal/deadline pode manter request pendente e ocupar concorrência.',s,'const res = await fetch(url, { ...opts, signal: AbortSignal.timeout(30000) });')

def data_scan(path, lines, findings):
    for i,l in enumerate(lines,1):
        s=l.strip()
        if re.search(r'(?i)\bSELECT\s+\*\b',l):
            add(findings,'MEDIUM','DATA',path,i,'SELECT-STAR','SELECT * amplia I/O, acopla consumidor ao schema e impede projeção/index-only scan.',s,re.sub(r'(?i)SELECT\s+\*','SELECT col1, col2, col3',s))
        if re.search(r'(?i)\bSELECT\b',l) and not re.search(r'(?i)\bLIMIT\b',l) and ('execute' in l or 'query' in l):
            add(findings,'MEDIUM','DATA',path,i,'QUERY-NO-LIMIT','Consulta potencialmente não paginada pode crescer sem limite e pressionar memória/latência.',s,s.rstrip('"\')')+' LIMIT ?')
        if ('execute(' in l or 'query(' in l) and (re.search(r'f["\'].*\b(SELECT|INSERT|UPDATE|DELETE)',l,re.I) or '% ' in l or '.format(' in l):
            add(findings,'CRITICAL','SECURITY',path,i,'SQL-INTERPOLATION','SQL interpolado pode permitir injeção e invalida cache de plano.',s,'cursor.execute("SELECT ... WHERE id = ?", (value,))')

def run_runtime_checks(sha):
    out=[]
    with tempfile.TemporaryDirectory(prefix='arbm-audit-') as td:
        p=subprocess.run(['git','archive',sha],stdout=subprocess.PIPE,check=True)
        tar=subprocess.run(['tar','-x','-C',td],input=p.stdout,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        checks=[
          ('python_compile',['python3','-m','compileall','-q','.'],120),
          ('python_unittest',['python3','-m','unittest','discover','-s','scripts','-p','test_*.py','-v'],600),
        ]
        for name,cmd,to in checks:
            try:
                r=subprocess.run(cmd,cwd=td,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=to)
                out.append({'name':name,'returncode':r.returncode,'output':r.stdout[-12000:]})
            except subprocess.TimeoutExpired as e:
                out.append({'name':name,'returncode':124,'output':f'TIMEOUT after {to}s\n'+((e.stdout or '') if isinstance(e.stdout,str) else '')[-8000:]})
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--sha',required=True); ap.add_argument('--out-dir',default='audit-out'); a=ap.parse_args()
    outdir=Path(a.out_dir); outdir.mkdir(parents=True,exist_ok=True)
    paths=git('ls-tree','-r','--name-only',a.sha).splitlines()
    findings=[]; inv=[]; hashes=defaultdict(list); ext_counts=Counter(); total_lines=0; text_files=0
    infra_seen={'docker':False,'k8s':False,'terraform':False,'workflow':False}
    for path in paths:
        raw=show(a.sha,path); h=hashlib.sha256(raw).hexdigest(); hashes[h].append(path)
        ext=Path(path).suffix.lower(); ext_counts[ext or '<none>']+=1
        name=Path(path).name.lower()
        if name.startswith('dockerfile') or name in {'docker-compose.yml','docker-compose.yaml'}: infra_seen['docker']=True
        if ext in {'.tf','.tfvars'}: infra_seen['terraform']=True
        if path.startswith('k8s/') or path.startswith('kubernetes/') or ('kind:' in raw[:2000].decode('utf-8','ignore') and ext in {'.yml','.yaml'}): infra_seen['k8s']=True
        if path.startswith('.github/workflows/'): infra_seen['workflow']=True
        nul=raw.count(b'\x00'); printable=sum((b in b'\t\n\r' or 32<=b<127 or b>=128) for b in raw)
        is_text=(nul==0 and (not raw or printable/max(1,len(raw))>.85))
        if not is_text:
            inv.append({'path':path,'bytes':len(raw),'lines':None,'sha256':h,'text':False}); continue
        text=raw.decode('utf-8','replace'); lines=text.splitlines(); total_lines+=len(lines); text_files+=1
        inv.append({'path':path,'bytes':len(raw),'lines':len(lines),'sha256':h,'text':True})
        line_rule_scan(path,lines,findings)
        if ext=='.py': python_scan(path,text,findings)
        if ext in {'.js','.mjs','.cjs','.ts','.tsx'}: js_scan(path,lines,findings)
        if ext in {'.py','.js','.mjs','.ts','.tsx','.sql'}: data_scan(path,lines,findings)
    for h,ps in hashes.items():
        if len(ps)>1:
            add(findings,'LOW','MAINTAINABILITY',ps[0],1,'DUPLICATE-FILE',f'Conteúdo idêntico também presente em: {", ".join(ps[1:])}; aumenta drift e custo de manutenção.','(arquivo duplicado)','Consolidar em fonte única/import compartilhado; manter apenas wrappers mínimos quando necessário.')
    if not infra_seen['docker']:
        add(findings,'INFO','INFRA','<repository>',0,'NO-DOCKERFILE','Não há Dockerfile/Compose versionado no SHA; limites de runtime dependem integralmente dos comandos de CI e imagens externas.','(ausente)','Adicionar imagem/runtime declarativo somente se o produto exigir container próprio; caso contrário documentar explicitamente a decisão.')
    if not infra_seen['k8s']:
        add(findings,'INFO','INFRA','<repository>',0,'NO-K8S','Não há manifests Kubernetes; VPC/NetworkPolicy/requests/limits de K8s não são aplicáveis a este repositório.','(ausente)','N/A até existir workload Kubernetes.')
    if not infra_seen['terraform']:
        add(findings,'INFO','INFRA','<repository>',0,'NO-TERRAFORM','Não há Terraform/IaC de cloud neste SHA; regras VPC/firewall não podem ser provadas por este repositório.','(ausente)','Versionar IaC quando houver recursos próprios que exijam VPC/firewall/rotas auditáveis.')
    all_text='\n'.join(show(a.sha,p).decode('utf-8','ignore') for p in paths if Path(p).suffix.lower() in TEXT_EXTS)
    if not re.search(r'(?i)opentelemetry|otel|traceparent|span_id|trace_id',all_text):
        add(findings,'MEDIUM','TELEMETRY','<repository>',0,'NO-DISTRIBUTED-TRACING','Não há instrumentação explícita de tracing distribuído; correlação entre ingress, provider e recovery depende de IDs/logs próprios.','(instrumentação OTel ausente)','Propagar trace_id/correlation_id em cada lane e exportar spans via OpenTelemetry quando houver backend FREE aprovado.')
    runtime=run_runtime_checks(a.sha)
    for r in runtime:
        if r['returncode']!=0:
            sev='HIGH' if r['name']=='python_compile' else 'MEDIUM'
            add(findings,sev,'TESTING','<runtime>',0,r['name'].upper(),f"Check remoto retornou código {r['returncode']}; baseline não passa integralmente essa verificação.",r['output'][-2000:],'Corrigir as falhas listadas e exigir returncode 0 como gate no SHA exato.')
    sev_order={'CRITICAL':0,'HIGH':1,'MEDIUM':2,'LOW':3,'INFO':4}; findings.sort(key=lambda x:(sev_order.get(x['severity'],9),x['path'],x['line'],x['rule']))
    summary={'sha':a.sha,'tracked_files':len(paths),'text_files':text_files,'total_text_lines':total_lines,'extensions':dict(ext_counts),'infra_seen':infra_seen,'findings_by_severity':dict(Counter(x['severity'] for x in findings)),'findings_by_category':dict(Counter(x['category'] for x in findings)),'runtime_checks':[{'name':r['name'],'returncode':r['returncode']} for r in runtime]}
    (outdir/'audit-findings.json').write_text(json.dumps({'summary':summary,'findings':findings,'runtime':runtime},indent=2,ensure_ascii=False),encoding='utf-8')
    (outdir/'audit-inventory.json').write_text(json.dumps(inv,indent=2,ensure_ascii=False),encoding='utf-8')
    md=['# ARBM SIST Black Belt Audit',f'Baseline: `{a.sha}`',f"Arquivos rastreados: {summary['tracked_files']} | arquivos texto: {text_files} | linhas texto inspecionadas: {total_lines}",'',f"Severidades: {summary['findings_by_severity']}",f"Categorias: {summary['findings_by_category']}",'','## Runtime checks']
    md += [f"- {r['name']}: returncode={r['returncode']}" for r in runtime]
    md += ['','## Findings']
    for f in findings:
        md += [f"### [{f['severity']}] {f['rule']} — `{f['path']}:{f['line']}`",f"**Impacto:** {f['impact']}",'','**Antes**','```',f['before'],'```','**Depois**','```',f['after'],'```','']
    (outdir/'audit-report.md').write_text('\n'.join(md),encoding='utf-8')
    print(json.dumps(summary,indent=2,ensure_ascii=False))
    print('TOP_FINDINGS')
    for f in findings[:60]: print(f"{f['severity']}|{f['category']}|{f['path']}:{f['line']}|{f['rule']}|{f['impact']}")

if __name__=='__main__': main()
