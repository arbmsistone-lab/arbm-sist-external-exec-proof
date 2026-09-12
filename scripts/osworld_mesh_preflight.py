"""Remote inference gate using recorded observations, before any VM smoke."""
import argparse,ast,base64,json,time
from pathlib import Path
from osworld_control import canonical_action,ground_action,pack_payload,validate_response,foreground_context,compact_tree
import osworld_free_mesh_shim as shim
from replay_osworld_run30 import load_cases
PNG_1X1 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAABe0lEQVR42u3asa6CMBQGYFB3nPsIOhhk0XSE93D0eRxITIghLD6DBlZhIOnIC7C44WJqWM4dSDopJhfQmvz/RAtDv3AawklNIjJ+OSPjxwMAAAAA8N1MXt0wTVO3tT79ZKGEtC2h9hf3ybQXM0oIAAAAAAAAAAAAAAAAvgYIw9BxnPV67ThOFEXN5HQ6bS7KsrRt+3q9Dvuj+TRvHyCi0+nEOa+qioiqquKcx3FMRJZlEZGUknOeZRl1S/tKOgFc103TVA0vl4vneQqw2WyCIKDOGRDAGJNSqqGUkjHWAHa73Xa7pT7SvpJRv9XY/L/Wde37/rCl38smns1mQgg1FELM53PDMMbjcZ7n9/t9v99/olv07xI6n8+c89vtpjZxkiRqD5RlyRgrikLfPUBEh8PBtu3VarVcLsMwbCYbABEdj8fFYvF4PIYDmK/aPqobo09fCK1FAAAAAAAAAAAAAAAAAAAArfL+qIGGx1ZQQjrFxMFXAAAAAIAu+QMm7VscSt4QYQAAAABJRU5ErkJggg=="

def call(body,already_packed=False):
 body['expected_build']=shim.EXPECTED_BUILD
 body['route_cooldowns']=shim.STATE['cooldowns']
 if already_packed:
  packed=dict(body);focused,active=foreground_context(packed['observation']);packed['observation']=compact_tree(focused,packed['instruction'],6500);packed['active_application']=active
  metrics={'after_bytes':len(json.dumps(packed).encode())}
 else:packed,metrics=pack_payload(body)
 evidence=[]
 for attempt in range(4):
  http,data=shim.request_mesh(packed);shim.track_attempts(data)
  evidence.append({'http':http,'data':data,'payload':metrics})
  if http==200:
   validate_response(data,shim.EXPECTED_PIPELINE,shim.EXPECTED_BUILD)
   action=ground_action(data.get('action'),packed.get('active_application','unknown'))
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
     if task=='001':assert x<70 or c.func.attr not in ('click','doubleClick','rightClick'),'REPLAY_REQUIRES_FOREGROUND_APP_RECOVERY'
     else:assert not (1750<=x<=1920 and 500<=y<=1080),'REPLAY_OCCLUDED_DESKTOP_COORDINATES'
   entry['grounding_regression']='PASS'
  for task in ('001','002','003'):
   step={'001':4,'002':3,'003':3}[task]
   recorded=next(Path('run38').rglob('osworld-sovereign-'+task+'/shim-observations/step_%04d.json'%step))
   original=json.loads(recorded.read_text(encoding='utf-8'))['request']
   body={k:original[k] for k in ('instruction','observation','screenshot_data_url','image_geometry','active_application')}
   body['fixture_provenance']={'run_id':34698877150,'task':task,'step':step}
   # Give the qualified text planner its documented token window; do not
   # turn burst exhaustion into a lower-quality fallback decision.
   waits=[(v/1000-time.time()) for k,v in shim.STATE['cooldowns'].items() if k.startswith('groq-accessibility-free:')]
   if len(waits)>=2 and min(waits)>0:time.sleep(min(65,min(waits)+1))
   body.update({'step':3,'memory':'Read the task source before editing outputs. Verify the current foreground before acting.','provider_hint':'text'})
   action,proof=call(body,already_packed=True)
   entry={'case':'run38-'+task,'action':action,'proof':proof,'provenance':body['fixture_provenance']};report.append(entry)
   assert isinstance(action.get('checkpoint'),dict) and action['checkpoint'].get('visible_text'),'SEMANTIC_CHECKPOINT_REQUIRED'
   nodes=ast.parse(action['command']).body
   if task=='001':
    assert not any(n.value.func.attr=='hotkey' and [ast.literal_eval(a) for a in n.value.args]==['ctrl','3'] for n in nodes),'SOURCE_NOT_READ'
    for n in nodes:
     if n.value.func.attr in ('click','doubleClick'):
      a=[ast.literal_eval(x) for x in n.value.args]
      assert not (len(a)>=2 and 70<=a[0]<=110 and 120<=a[1]<=155),'PREMATURE_CALENDAR'
   if task=='002':
    for n in nodes:
     if n.value.func.attr=='click':
      a=[ast.literal_eval(x) for x in n.value.args]
      assert not (len(a)>=2 and a[0]>1750 and a[1]>750 and len(nodes)==1),'SINGLE_CLICK_DOES_NOT_OPEN_SOURCE'
   if task=='003':
    assert not any(n.value.func.attr=='hotkey' and set(str(ast.literal_eval(a)).lower() for a in n.value.args) in ({'ctrl','win','d'},{'alt','tab'},{'ctrl','super','d'}) for n in nodes),'OPEN_ARCHIVE_MUST_NOT_BE_ABANDONED'
    assert 'filter.zip' in action.get('verification','').lower() or 'filter' in action.get('plan','').lower(),'ACTUAL_OPEN_ARCHIVE_NOT_RECOGNIZED'
   entry['semantic_regression']='PASS'
  assert any(e['data'].get('model','').startswith('openai/gpt-oss') and e['http']==200 for r in report for e in r['proof']),'TERTIARY_FREE_ROUTE_NOT_PROVEN'
  return report
 finally:
  Path('osworld-mesh-preflight.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
  print(json.dumps([{'case':x['case'],'action':x['action'],'grounding_regression':x.get('grounding_regression')} for x in report]))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('directory');args=p.parse_args();main(args.directory)
