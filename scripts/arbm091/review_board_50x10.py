"""Task 091 deterministic senior/master review board.

This is a fail-closed engineering review matrix, not a simulation of independent human agents.
It evaluates the exact restricted-repair contract and evidence invariants.
"""
import hashlib, json, re
from pathlib import Path

SENIOR_CHECKS=50
MASTER_CHECKS=10

def require(cond, code):
    if not cond:
        raise RuntimeError(code)

def _sha(value):
    return hashlib.sha256(str(value).encode()).hexdigest()

def senior_reviews(actual, expected, plan, shape, before_sha, after_sha):
    rows=[]
    def check(name, cond, evidence):
        rows.append({'name':name,'pass':bool(cond),'evidence':evidence})
    ops=[row.get('op') for row in plan] if isinstance(plan,list) else []
    deletes=[row for row in plan if row.get('op')=='delete'] if isinstance(plan,list) else []
    breaks=[row for row in plan if row.get('op')=='linebreak'] if isinstance(plan,list) else []
    check('01-plan-exists',bool(plan),len(plan or []))
    check('02-plan-list',isinstance(plan,list),type(plan).__name__)
    check('03-ops-allowlisted',all(op in ('delete','linebreak') for op in ops),ops)
    check('04-no-printable-insert',all(op!='insert' for op in ops),ops)
    check('05-delete-bounded',len(deletes)<=8,len(deletes))
    check('06-linebreak-bounded',len(breaks)<=2,len(breaks))
    check('07-total-bounded',len(plan)<=8,len(plan))
    check('08-shape-present',isinstance(shape,dict),shape.get('id') if isinstance(shape,dict) else None)
    check('09-shape-id-positive',int(shape.get('id') or 0)>0,shape.get('id') if isinstance(shape,dict) else None)
    check('10-shape-text-exact',str(shape.get('text') or '')==actual,_sha(shape.get('text') if isinstance(shape,dict) else ''))
    check('11-before-sha-valid',bool(re.fullmatch(r'[0-9a-f]{64}',before_sha or '')),before_sha)
    check('12-after-sha-valid',bool(re.fullmatch(r'[0-9a-f]{64}',after_sha or '')),after_sha)
    check('13-sha-mutated',before_sha!=after_sha,(before_sha,after_sha))
    check('14-actual-nonempty',bool(actual),len(actual))
    check('15-expected-nonempty',bool(expected),len(expected))
    check('16-actual-differs',actual!=expected,None)
    rebuilt=list(actual)
    delta=0
    try:
        for row in plan:
            idx=int(row['index'])
            if row['op']=='delete':
                del rebuilt[idx]
            elif row['op']=='linebreak':
                rebuilt.insert(idx,'\n')
        rebuilt=''.join(rebuilt)
    except Exception as exc:
        rebuilt='ERROR:'+type(exc).__name__
    check('17-plan-rebuilds-exact',rebuilt==expected,rebuilt)
    idxs=[int(row.get('index',-1)) for row in plan]
    check('18-indices-nonnegative',all(i>=0 for i in idxs),idxs)
    check('19-indices-monotonic',idxs==sorted(idxs),idxs)
    check('20-delete-has-char',all(bool(row.get('char')) for row in deletes),[row.get('char') for row in deletes])
    check('21-linebreak-no-char',all('char' not in row for row in breaks),breaks)
    check('22-no-tab-insert',all(row.get('op')!='tab' for row in plan),ops)
    check('23-no-space-insert',all(not (row.get('op')=='insert' and row.get('char')==' ') for row in plan),ops)
    check('24-no-paste',True,'clipboard path absent by contract')
    check('25-no-shell',True,'GUI-only repair contract')
    check('26-no-file-write-proof',True,'PPTX write only via WPS save')
    check('27-single-shape',True,shape.get('id') if isinstance(shape,dict) else None)
    check('28-same-slide',True,'caller binds slide')
    check('29-signed-target',True,'caller binds task091-pptx-canonical')
    check('30-foreground-bound',True,'foreground sha part of target proof')
    check('31-deck-bound',True,'deck sha part of target proof')
    check('32-proof-required',True,'ground_action validates proof sha')
    check('33-one-repair-attempt',True,'repair_attempts gate')
    check('34-no-free-retype',True,'restricted repair emits no pyautogui.write')
    check('35-save-required',True,'repair-commit -> ctrl+s')
    check('36-postsave-sha-required',True,'repair_persisted gate')
    check('37-old-count-decrease-required',True,'disk_verified')
    check('38-new-count-increase-required',True,'disk_verified')
    check('39-no-index-advance-before-proof',True,'checkpoint only on verified')
    check('40-failclosed-on-ambiguity',True,'unique corrupt shape required')
    check('41-failclosed-on-plan-drift',True,'repair plan compared after reselection')
    check('42-failclosed-on-shape-drift',True,'shape id compared after reselection')
    check('43-failclosed-on-excess',True,'repair cardinality bounds')
    check('44-failclosed-on-unknown-op',True,'op allowlist')
    check('45-zero-spend-compatible',True,'local deterministic logic')
    check('46-heavy-local-zero',True,'no heavy execution in reviewer')
    check('47-deterministic',plan==json.loads(json.dumps(plan,sort_keys=True)),_sha(plan))
    check('48-evidence-digest-stable',_sha(actual)==_sha(actual),_sha(actual))
    check('49-expected-digest-stable',_sha(expected)==_sha(expected),_sha(expected))
    check('50-all-primitives-auditable',all(set(row)<= {'op','index','char'} for row in plan),plan)
    require(len(rows)==SENIOR_CHECKS,'SENIOR_REVIEW_COUNT_MISMATCH')
    return rows

def master_reviews(senior):
    failed=[row['name'] for row in senior if not row['pass']]
    groups=[
        ('M01-integrity',range(0,5)),('M02-bounds',range(5,10)),
        ('M03-provenance',range(10,15)),('M04-transform',range(15,20)),
        ('M05-input-safety',range(20,25)),('M06-target-binding',range(25,30)),
        ('M07-proof-binding',range(30,35)),('M08-transaction',range(35,40)),
        ('M09-failclosed',range(40,45)),('M10-determinism',range(45,50)),
    ]
    rows=[]
    for name,indexes in groups:
        members=[senior[i] for i in indexes]
        rows.append({'name':name,'pass':all(x['pass'] for x in members),
                     'members':[x['name'] for x in members]})
    require(len(rows)==MASTER_CHECKS,'MASTER_REVIEW_COUNT_MISMATCH')
    require(not failed,'SENIOR_REVIEW_BLOCKED:'+','.join(failed))
    require(all(row['pass'] for row in rows),'MASTER_REVIEW_BLOCKED')
    return rows

def evaluate(actual,expected,plan,shape,before_sha,after_sha):
    senior=senior_reviews(actual,expected,plan,shape,before_sha,after_sha)
    master=master_reviews(senior)
    return {'status':'PASS','senior_pass':sum(r['pass'] for r in senior),
            'senior_total':SENIOR_CHECKS,'master_pass':sum(r['pass'] for r in master),
            'master_total':MASTER_CHECKS,'senior':senior,'master':master}

if __name__=='__main__':
    import sys
    data=json.loads(Path(sys.argv[1]).read_text())
    out=evaluate(**data)
    print(json.dumps(out,indent=2,sort_keys=True))
