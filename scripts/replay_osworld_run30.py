"""Replay recorded run30 observations; never start OSWorld or execute GUI code."""
import argparse,base64,json,re,hashlib,sys
from pathlib import Path
from osworld_control import Verifier,canonical_action,pack_payload

def load_cases(root):
 for task in ('001','002','003'):
  d=next(root.rglob('osworld-sovereign-'+task))
  trajectory=[json.loads(x) for x in next(d.rglob('traj.jsonl')).read_text(encoding='utf-8').splitlines()]
  runtime=next(d.rglob('runtime.log')).read_text(encoding='utf-8')
  trees=re.findall(r'LINEAR AT: (.*?)(?=Generating content)',runtime,re.S)
  log=(d/'osworld.log').read_text(encoding='utf-8')
  instruction=next(x.split('[Instruction]:',1)[1].strip() for x in log.splitlines() if '[Instruction]:' in x)
  yield task,d,trajectory,trees,instruction

def replay(root):
 report=[]
 for task,d,traj,trees,instruction in load_cases(root):
  v=Verifier();rejected=[];no_progress=[];sizes=[];first_no_effect=None;idle_increments=0;previous_np=0
  for i,(step,obs) in enumerate(zip(traj,trees)):
   image=''
   if i:
    prev=next(d.rglob(traj[i-1]['screenshot_file']))
    image='data:image/png;base64,'+base64.b64encode(prev.read_bytes()).decode()
   pending_before=v.pending
   result=v.observe(obs,image)
   if not pending_before and result['no_progress']!=previous_np: idle_increments+=1
   previous_np=result['no_progress']
   if not result['progress'] and i and first_no_effect is None:first_no_effect=i+1
   no_progress.append(v.no_progress)
   _,size=pack_payload({'instruction':instruction,'observation':obs,'memory':'','screenshot_data_url':image})
   sizes.append(size)
   command=step['action']
   if command not in ('WAIT','FAIL','DONE'):
    try:canonical_action({'action':'exec','command':command});v.issued(command)
    except ValueError as e:rejected.append({'step':i+1,'reason':str(e),'command_sha256':hashlib.sha256(command.encode()).hexdigest()})
  report.append({'task':task,'recorded_steps':len(traj),'first_no_effect_observation':first_no_effect,
                 'rejected_commands':rejected,'max_no_progress':max(no_progress),'idle_no_progress_increments':idle_increments,'first_recovery_exhaustion':next((i+1 for i,n in enumerate(no_progress) if n>=12),None),
                 'max_payload_before_bytes':max(x['before_bytes'] for x in sizes),'max_payload_after_bytes':max(x['after_bytes'] for x in sizes),
                 'official_score_unchanged':float(next(d.rglob('result.txt')).read_text()),'replay':'PASS'})
  assert idle_increments==0,task
  assert max(x['after_bytes'] for x in sizes)<=420000,task
 assert sum(len(x['rejected_commands']) for x in report)>0
 assert any(x['max_no_progress']>=12 for x in report)
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--output',default='run30-replay.json');a=p.parse_args()
 result=replay(Path(a.directory));Path(a.output).write_text(json.dumps(result,indent=2),encoding='utf-8')
 print(json.dumps(result,indent=2))
