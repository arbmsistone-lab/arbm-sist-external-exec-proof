"""Task-061 calibrated color-grade specialist.

Learns only from the user-visible reference original/edited pair inside the
OSWorld guest. It never reads evaluator ground truth or host files.
"""
import base64
import re
from osworld_gimp_style_transfer import parse_reference_pair_task

DONE = re.compile(r'ARBM061_DONE\s+rmse=([0-9.]+)\s+model=([A-Za-z0-9_-]+)')
UNSAFE = re.compile(r'ARBM061_REF_MODEL_UNSAFE\s+rmse=([0-9.]+)')
PREEXIST = re.compile(r'ARBM061_OUTPUT_PREEXISTED')


def _action(command, plan, phase):
    return {'action':'exec','command':command,'plan':plan,'summary':plan,
            'expected_change':phase,'confidence':1.0,'observed_facts':[],
            'verification':'next foreground must expose '+phase,
            'checkpoint':None,'specialist_phase':phase}


def _guest_script(task):
    ro=task['reference_original']; redit=task['reference_edited']
    target=task['target_original']; output=task['output']
    return f'''import numpy as np, hashlib\nfrom PIL import Image\nfrom pathlib import Path\np=Path.home()/"Pictures"\nout=p/"{output}"\nif out.exists(): print("ARBM061_OUTPUT_PREEXISTED"); raise SystemExit(4)\nR=Image.Resampling.BILINEAR\ndef im(n): return Image.open(p/n).convert("RGB")\na=np.asarray(im("{ro}").resize((756,1008),R),dtype=np.float32)/255\nb=np.asarray(im("{redit}").resize((756,1008),R),dtype=np.float32)/255\na=a.reshape(-1,3); b=b.reshape(-1,3)\nidx=np.arange(len(a)); tr=idx%5!=0; va=~tr\ndef f(x):\n r,g,z=x.T; return np.stack((np.ones(len(x)),r,g,z,r*r,g*g,z*z,r*g,r*z,g*z,r*r*r,g*g*g,z*z*z,r*r*g,r*r*z,g*g*r,g*g*z,z*z*r,z*z*g,r*g*z),1)\nX=f(a[tr]); Y=b[tr]; q=X.T@X+np.eye(X.shape[1],dtype=np.float32)*1e-5; w=np.linalg.solve(q,X.T@Y)\npred=np.clip(f(a[tr])@w,0,1); u=np.clip(a[tr]*255,0,255).astype(np.uint8); res=(Y-pred)*255\nl=[]\nfor c in range(3):\n s=np.bincount(u[:,c],weights=res[:,c],minlength=256); n=np.bincount(u[:,c],minlength=256); good=n>0; x=np.arange(256); l.append(np.interp(x,x[good],s[good]/n[good]).astype(np.float32))\ndef apply(x):\n y=np.clip(f(x)@w,0,1)*255; u=np.clip(x*255,0,255).astype(np.uint8); y+=np.stack([l[c][u[:,c]] for c in range(3)],1); return np.clip(y,0,255)\ny=apply(a[va]/1.0); rmse=float(np.sqrt(np.mean((y-b[va]*255)**2)))\nprint(f"ARBM061_REF_RMSE={{rmse:.4f}}")\nif rmse>20: print(f"ARBM061_REF_MODEL_UNSAFE rmse={{rmse:.4f}}"); raise SystemExit(3)\nt=im("{target}"); A=np.asarray(t,dtype=np.uint8); O=np.empty_like(A)\nfor yy in range(0,A.shape[0],64):\n x=A[yy:yy+64].reshape(-1,3).astype(np.float32)/255; O[yy:yy+64]=apply(x).round().astype(np.uint8).reshape(A[yy:yy+64].shape)\nImage.fromarray(O).save(out,quality=100,subsampling=0)\nz=Image.open(out); assert z.size==t.size and z.mode=="RGB"\nraw=out.read_bytes(); assert len(raw)>1024; sha=hashlib.sha256(raw).hexdigest()\nprint(f"ARBM061_DONE rmse={{rmse:.4f}} model=poly3_residual size={{z.size[0]}}x{{z.size[1]}} sha256={{sha}} bytes={{len(raw)}}")\n'''

def next_calibrated_action(instruction, active_application, observation, state):
    task=parse_reference_pair_task(instruction)
    if not task or state.get('terminal_failed'):
        return None
    obs=str(observation or ''); app=str(active_application or '').casefold()
    terminal=('terminal' in app or 'terminal' in obs.casefold())
    if PREEXIST.search(obs):
        state['hard_fail']='OUTPUT_PREEXISTED'
        return None
    done=DONE.search(obs)
    if done:
        state['done']=True; state['reference_rmse']=float(done.group(1))
        return {'action':'finish','command':'','plan':'Finish after calibrated reference-pair validation and output creation.',
                'summary':'Reference-calibrated target edit saved by the agent.','confidence':1.0,
                'verification':done.group(0)}
    bad=UNSAFE.search(obs)
    if bad and not state.get('fallback_requested'):
        state['reference_rmse']=float(bad.group(1)); state['fallback_requested']=True
        return _action("pyautogui.hotkey('alt','f4'); pyautogui.sleep(1.0)",
                       'Close the calibration terminal and fall back without creating an unsafe output.', '061-calibration-fallback')
    if state.get('fallback_requested'):
        if terminal:
            state['fallback_waits']=state.get('fallback_waits',0)+1
            return None
        state['terminal_failed']=True; state['owned']=False
        return None
    if not state.get('launch_requested'):
        state['owned']=True; state['launch_requested']=True
        return _action("pyautogui.press('win'); pyautogui.sleep(0.8); pyautogui.write('Terminal', interval=0.05); pyautogui.press('enter'); pyautogui.sleep(1.5)",
                       'Open the remote OSWorld terminal through the desktop launcher.', '061-terminal-visible')
    if not terminal:
        state['launch_waits']=state.get('launch_waits',0)+1
        return None
    if state.get('script_requested') and 'ARBM061_SCRIPT_READY' not in obs and not state.get('run_requested'):
        state['script_waits']=state.get('script_waits',0)+1
        if state['script_waits'] <= 3:
            return None
        state['script_requested']=False; state['script_waits']=0
    if not state.get('script_requested'):
        payload=base64.b64encode(_guest_script(task).encode()).decode()
        shell="python3 -c \"import base64;open('/tmp/arbm061.py','wb').write(base64.b64decode('"+payload+"'))\"; echo ARBM061_SCRIPT_READY"
        state['script_requested']=True
        return _action("pyautogui.write(%r, interval=0.001); pyautogui.press('enter'); pyautogui.sleep(1.2)" % shell,
                       'Install the bounded task-specific calibration script inside the remote guest.', 'ARBM061_SCRIPT_READY')
    if 'ARBM061_SCRIPT_READY' in obs and not state.get('run_requested'):
        state['run_requested']=True
        return _action("pyautogui.write('python3 /tmp/arbm061.py', interval=0.03); pyautogui.press('enter')",
                       'Fit the color-grade transform on the visible reference pair, validate it, and apply it only if safe.', 'ARBM061_REF_RMSE')
    if state.get('run_requested'):
        state['run_waits']=state.get('run_waits',0)+1
        if state['run_waits']>12:
            state['fallback_requested']=True
            return _action("pyautogui.hotkey('alt','f4'); pyautogui.sleep(1.0)", 'Calibration produced no bounded proof; close terminal and fall back fail-closed.', '061-calibration-timeout')
        return None
    return None
