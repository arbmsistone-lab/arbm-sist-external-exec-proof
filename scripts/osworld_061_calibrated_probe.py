"""Non-scoring official-VM probe for the calibrated task-061 champion."""
import base64, hashlib, json, os, re, sys
from pathlib import Path
from osworld_061_calibrated_grade import _guest_script
DONE=re.compile(r'ARBM061_DONE\s+rmse=([0-9.]+)\s+model=([A-Za-z0-9_-]+)')
UNSAFE=re.compile(r'ARBM061_REF_MODEL_UNSAFE\s+rmse=([0-9.]+)')
TASK={'reference_original':'IMG_7328_original.jpg','reference_edited':'IMG_7328_edited.jpg',
      'target_original':'IMG_7318_original.jpg','output':'IMG_7318_edited.jpg'}
def sha(path):
    with open(path,'rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def step(env,cmd,pause=1): return env.step(cmd,pause=pause)[0]
def tree(obs): return str((obs or {}).get('accessibility_tree') or '')
def main(image,evidence):
    if os.environ.get('RUNNER_ENVIRONMENT')!='github-hosted' or os.environ.get('ZERO_SPEND_MODE')!='HARD':
        raise RuntimeError('CLOUD_ZERO_SPEND_PROBE_REQUIRED')
    from desktop_env.desktop_env import DesktopEnv
    from task_loader import load_task_from_file
    evidence=Path(evidence); evidence.mkdir(parents=True,exist_ok=True)
    base_before=sha(image); env=None
    proof={'purpose':'calibrated task-061 champion probe only; no evaluator/score',
           'candidate_sha':os.environ.get('GITHUB_SHA'),'zero_spend_mode':'HARD','heavy_local':0,'status':'NOT_PROVEN'}
    try:
        task=load_task_from_file('evaluation_examples/task_class/task_061.py')
        env=DesktopEnv(provider_name='docker',path_to_vm=str(image),headless=True,
                       action_space='pyautogui',require_a11y_tree=True,volume_size=50)
        env.reset(task_config=task)
        obs=step(env,"pyautogui.hotkey('ctrl','alt','t'); pyautogui.sleep(2)",3)
        for _ in range(12):
            if 'terminal' in tree(obs).casefold(): break
            obs=step(env,"pyautogui.sleep(1)",1)
        else: raise RuntimeError('TERMINAL_NOT_VISIBLE')
        payload=base64.b64encode(_guest_script(TASK).encode()).decode()
        shell="python3 -c \"import base64;open('/tmp/arbm061.py','wb').write(base64.b64decode('"+payload+"'))\"; echo ARBM061_SCRIPT_READY"
        obs=step(env,"pyautogui.write(%r, interval=0.001); pyautogui.press('enter'); pyautogui.sleep(2)"%shell,2)
        if 'ARBM061_SCRIPT_READY' not in tree(obs): raise RuntimeError('CALIBRATION_SCRIPT_NOT_VISIBLE')
        step(env,"pyautogui.write('python3 /tmp/arbm061.py', interval=0.03); pyautogui.press('enter')",1)
        match=None
        for i in range(90):
            obs=step(env,"pyautogui.sleep(2)",2)
            t=tree(obs); (evidence/f'obs-{i:03d}.txt').write_text(t,encoding='utf-8')
            bad=UNSAFE.search(t)
            if bad: raise RuntimeError('REFERENCE_MODEL_UNSAFE:'+bad.group(1))
            match=DONE.search(t)
            if match: break
        if not match: raise RuntimeError('CALIBRATED_DONE_MARKER_UNPROVEN')
        rmse=float(match.group(1))
        if rmse>20: raise RuntimeError('REFERENCE_RMSE_ABOVE_FULL_SCORE_BOUND')
        output='/home/user/Pictures/IMG_7318_edited.jpg'
        data=env.controller.get_file(output)
        if not isinstance(data,(bytes,bytearray)) or len(data)<1024: raise RuntimeError('CALIBRATED_OUTPUT_BYTES_UNPROVEN')
        digest=hashlib.sha256(data).hexdigest(); (evidence/'IMG_7318_edited.jpg').write_bytes(data)
        proof.update(status='CALIBRATED_EXPORT_PROVEN',reference_rmse=rmse,model=match.group(2),
                     output='IMG_7318_edited.jpg',output_bytes=len(data),output_sha256=digest)
    finally:
        if env is not None: env.close()
        after=sha(image); proof.update(qcow_base_before=base_before,qcow_base_after=after)
        if after!=base_before: proof.update(status='NOT_PROVEN',failure='PINNED_QCOW_BASE_MODIFIED')
        (evidence/'calibrated-probe-result.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
        if after!=base_before: raise RuntimeError('PINNED_QCOW_BASE_MODIFIED')
    if proof.get('status')!='CALIBRATED_EXPORT_PROVEN': raise RuntimeError('CALIBRATED_EXPORT_UNPROVEN')
    print(json.dumps({'status':proof['status'],'reference_rmse':proof['reference_rmse'],
                      'output':proof['output'],'bytes':proof['output_bytes']}))
if __name__=='__main__':
    main(Path(sys.argv[1]),Path(sys.argv[2]))
