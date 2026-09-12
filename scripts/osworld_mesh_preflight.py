"""Remote inference gate using recorded observations, before any VM smoke."""
import argparse,ast,base64,json,time
from pathlib import Path
from osworld_control import canonical_action,pack_payload,validate_response
import osworld_free_mesh_shim as shim
from replay_osworld_run30 import load_cases
PNG_1X1 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAABe0lEQVR42u3asa6CMBQGYFB3nPsIOhhk0XSE93D0eRxITIghLD6DBlZhIOnIC7C44WJqWM4dSDopJhfQmvz/RAtDv3AawklNIjJ+OSPjxwMAAAAA8N1MXt0wTVO3tT79ZKGEtC2h9hf3ybQXM0oIAAAAAAAAAAAAAAAAvgYIw9BxnPV67ThOFEXN5HQ6bS7KsrRt+3q9Dvuj+TRvHyCi0+nEOa+qioiqquKcx3FMRJZlEZGUknOeZRl1S/tKOgFc103TVA0vl4vneQqw2WyCIKDOGRDAGJNSqqGUkjHWAHa73Xa7pT7SvpJRv9XY/L/Wde37/rCl38smns1mQgg1FELM53PDMMbjcZ7n9/t9v99/olv07xI6n8+c89vtpjZxkiRqD5RlyRgrikLfPUBEh8PBtu3VarVcLsMwbCYbABEdj8fFYvF4PIYDmK/aPqobo09fCK1FAAAAAAAAAAAAAAAAAAAArfL+qIGGx1ZQQjrFxMFXAAAAAIAu+QMm7VscSt4QYQAAAABJRU5ErkJggg=="

def call(body):
 body['expected_build']=shim.EXPECTED_BUILD
 body['route_cooldowns']=shim.STATE['cooldowns']
 packed,metrics=pack_payload(body)
 evidence=[]
 for attempt in range(4):
  http,data=shim.request_mesh(packed);shim.track_attempts(data)
  evidence.append({'http':http,'data':data,'payload':metrics})
  if http==200:
   validate_response(data,shim.EXPECTED_PIPELINE,shim.EXPECTED_BUILD)
   action=canonical_action(data.get('action'))
   assert action['action']=='exec',data
   return action,evidence
  if http not in (429,503):break
  time.sleep(20)
 raise RuntimeError(json.dumps(evidence))

def main(directory):
 report=[]
 try:
  action,proof=call({'instruction':"Activate the visibly focused OK button with pyautogui.press('enter').",'observation':'push-button OK focused','screenshot_data_url':'data:image/png;base64,'+PNG_1X1,'step':1,'memory':''})
  report.append({'case':'contract','action':action,'proof':proof})
  for task,d,traj,trees,instruction in load_cases(Path(directory)):
   # Observation preceding an actual failed action, with its matching prior screenshot.
   index=2 if task=='001' else 1
   screenshot=next(d.rglob(traj[index-1]['screenshot_file']))
   action,proof=call({'instruction':instruction,'observation':trees[index],
                     'screenshot_data_url':'data:image/png;base64,'+base64.b64encode(screenshot.read_bytes()).decode(),
                     'step':index+1,'memory':'Previous click had no useful effect. Reassess which window is in front.',
                     'no_progress_count':2,'previous_command':traj[index-1]['action']})
   entry={'case':'run30-'+task,'action':action,'proof':proof};report.append(entry)
   # Regression: never issue the recorded click at an occluded target again.
   nodes=ast.parse(action['command']).body
   for n in nodes:
    c=n.value
    if c.func.attr in ('click','doubleClick','rightClick'):
     args=[ast.literal_eval(x) for x in c.args];kw={k.arg:ast.literal_eval(k.value) for k in c.keywords}
     x=kw.get('x',args[0] if args else -1);y=kw.get('y',args[1] if len(args)>1 else -1)
     if task=='001':assert not (350<=x<=680 and 140<=y<=320),'REPLAY_STALE_THUNDERBIRD_COORDINATES'
     else:assert not (1750<=x<=1920 and 550<=y<=1000),'REPLAY_OCCLUDED_DESKTOP_COORDINATES'
   entry['grounding_regression']='PASS'
  return report
 finally:
  Path('osworld-mesh-preflight.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
  print(json.dumps([{'case':x['case'],'action':x['action'],'grounding_regression':x.get('grounding_regression')} for x in report]))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory');args=p.parse_args();main(args.directory)
