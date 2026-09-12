"""Portable evidence sealing and strict official smoke aggregation."""
import argparse
import hashlib
import json
import math
from pathlib import Path

REQUIRED = ('candidate-sha.txt','zero-spend-mode.txt','osworld-agent-version.txt','task-id.txt','task-rc.txt',
            'endpoint-manifest.json','osworld.log','provider-telemetry.jsonl')

def seal(root):
    files=sorted(p for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt')
    (root/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(root).as_posix()+'\n' for p in files),encoding='utf-8')

def verify(root):
    listed=set()
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        digest,name=line.split('  ',1)
        p=(root/name).resolve()
        if not p.is_relative_to(root.resolve()) or name in listed:raise ValueError('UNSAFE_CHECKSUM_PATH')
        listed.add(name)
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise ValueError('CHECKSUM_MISMATCH:'+name)
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    if listed!=actual:raise ValueError('CHECKSUM_COVERAGE')
    return len(listed)

def aggregate(root):
    dirs=sorted(p.parent for p in root.rglob('task-id.txt'))
    if len(dirs)!=3:raise ValueError('EXPECTED_3_TASKS')
    scores=[];ids=[];manifests=[];commits=[]
    for d in dirs:
        verify(d)
        for name in REQUIRED:
            if not (d/name).is_file():raise ValueError('MISSING_EVIDENCE:'+name)
        task=(d/'task-id.txt').read_text().strip();ids.append(task)
        if (d/'task-rc.txt').read_text().strip()!='0':raise ValueError('TASK_RC:'+task)
        if (d/'zero-spend-mode.txt').read_text().strip()!='HARD':raise ValueError('ZERO_SPEND_MODE')
        files=list(d.glob('results/**/result.txt'))
        if len(files)!=1:raise ValueError('OFFICIAL_RESULT_COUNT')
        score=float(files[0].read_text().strip())
        if not math.isfinite(score) or not 0<=score<=1:raise ValueError('INVALID_SCORE')
        summaries=list(d.glob('results/**/results.json'))
        if len(summaries)!=1:raise ValueError('OFFICIAL_SUMMARY_MISSING')
        summary=json.loads(summaries[0].read_text())
        if len(summary)!=1 or summary[0].get('task_id')!=task or summary[0].get('status')!='success' or summary[0].get('score')!=score:raise ValueError('EVALUATOR_SUMMARY_MISMATCH')
        manifest=json.loads((d/'endpoint-manifest.json').read_text())
        manifests.append(json.dumps(manifest,sort_keys=True));commits.append((d/'candidate-sha.txt').read_text().strip())
        telemetry=[json.loads(x) for x in (d/'provider-telemetry.jsonl').read_text(encoding='utf-8').splitlines()]
        issued=False
        for x in telemetry:
            if x.get('status')=='SHIM_ERROR' or (x.get('status')=='TERMINAL_FAIL' and x.get('reason') not in ('RECOVERY_EXHAUSTED','STEP_BUDGET')):raise ValueError('FATAL_AGENT:'+task)
            if x.get('http')==200:
                if x.get('agent_build')!=manifest['agent_build']:raise ValueError('ENDPOINT_CHANGED')
                if x.get('mandatory_cost_usd')!=0 or x.get('paid_fallback_used') is not False:raise ValueError('ZERO_SPEND_UNPROVEN')
                if not any(a.get('model')==x.get('model') and a.get('status')==200 and (a.get('free_plan_proven') or a.get('zero_spend_confirmed')) for a in x.get('provider_attempts',[])):raise ValueError('FREE_PROVIDER_UNPROVEN')
                issued=True
        if not issued:raise ValueError('PROVIDER_TELEMETRY_MISSING')
        scores.append(score)
    if sorted(ids)!=['001','002','003']:raise ValueError('TASK_ID_SET')
    if len(set(manifests))!=1 or len(set(commits))!=1:raise ValueError('MIXED_BUILD_OR_COMMIT')
    if max(scores)<=0:raise ValueError('ZERO_SCORE_OSWORLD_RUN')
    return {'aggregate':'SUCCESS','task_ids':ids,'scores':scores,'zero_spend_mode':'HARD','paid_fallback_used':False,'commit':commits[0]}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['seal','verify','aggregate']);p.add_argument('directory');a=p.parse_args()
    out=globals()[a.mode](Path(a.directory));print(json.dumps(out))
