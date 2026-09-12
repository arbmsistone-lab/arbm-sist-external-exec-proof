import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from osworld_control import Verifier
ROOT = pathlib.Path(r'C:\Users\airto\AppData\Local\Temp\run34')
for task in ('001','002','003'):
    base = ROOT / f'osworld-sovereign-{task}'
    events = [json.loads(x) for x in (base/f'osworld-free-mesh-shim-{task}.log').read_text(encoding='utf-8').splitlines() if x.strip()]
    issued = {int(e['step']): e['command'] for e in events if e.get('status') == 'ACTION_ISSUED'}
    obs_files = sorted((base/'shim-observations').glob('step_*.json'))
    v = Verifier(); old_max = 0; new_max = 0
    for p in obs_files:
        step = int(p.stem.split('_')[1])
        if step > 1 and step-1 in issued: v.issued(issued[step-1])
        d = json.loads(p.read_text(encoding='utf-8'))['request']
        r = v.observe(d.get('observation',''), d.get('screenshot_data_url',''))
        new_max = max(new_max, r['no_progress'])
    for e in events:
        old_max = max(old_max, int((e.get('verifier') or {}).get('no_progress') or 0))
    waits = sum(1 for e in events if e.get('status') == 'WAIT_RECOVERY')
    print(json.dumps({'task':task,'actions':len(issued),'waits':waits,'old_max_no_progress':old_max,'new_max_no_progress':new_max,'new_final_no_progress':v.no_progress,'recovery_level':v.recovery_level}))
print('RUN34_REPLAY_ELITE_PASS')