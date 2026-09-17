import argparse,asyncio,base64,json,os
from pathlib import Path
from decimal import Decimal
from openai import OpenAI
from playwright.async_api import async_playwright
MODEL=os.environ.get('ARBM_WEB_MODEL','dots-studio/dots-3-note-preview:free'); client=OpenAI(base_url='https://openrouter.ai/api/v1',api_key=os.environ['OPENROUTER_API_KEY'],timeout=45,max_retries=0)
TOOL=[{'type':'function','function':{'name':'browser_action','description':'One browser action grounded in current evidence.','parameters':{'type':'object','properties':{'action':{'type':'string','enum':['click_text','fill','select','press','scroll','wait','done','fail']},'target':{'type':'string'},'value':{'type':'string'},'key':{'type':'string'},'task_type':{'type':'string','enum':['RETRIEVE','MUTATE','NAVIGATE']},'retrieved_data':{},'reason':{'type':'string'}},'required':['action'],'additionalProperties':False}}}]
SYSTEM='Use only browser_action. Ground every action in current screenshot and visible text. Never use memorized benchmark answers. One action per turn. click_text needs visible text; fill/select target a visible label, placeholder or name. Use done only after the requested outcome is visibly established; for retrieval return structured retrieved_data.'
def load(path,tid): return next(x for x in json.loads(Path(path).read_text()) if int(x['task_id'])==tid)
def zero(r):
 d=r.model_dump(); u=d.get('usage') or {}; cost=u.get('cost')
 if d.get('model')!=MODEL: raise RuntimeError('MODEL_IDENTITY_MISMATCH')
 if cost is None or Decimal(str(cost))!=0: raise RuntimeError('ZERO_SPEND_NOT_PROVEN')
 return {'prompt_tokens':u.get('prompt_tokens'),'completion_tokens':u.get('completion_tokens'),'cost':str(cost)}
async def fill(page,target,value):
 for loc in (page.get_by_label(target,exact=False),page.get_by_placeholder(target,exact=False),page.locator('[name="'+target+'"]')):
  try:
   if await loc.count(): await loc.first.fill(value); return
  except Exception: pass
 raise RuntimeError('FIELD_NOT_FOUND:'+target)
async def main(a):
 task=load(a.tasks,a.task_id); out=Path(a.output)/str(a.task_id); out.mkdir(parents=True,exist_ok=True); hist=[]; costs=[]; result=None
 async with async_playwright() as p:
  br=await p.chromium.launch(headless=True,args=['--no-sandbox']); ctx=await br.new_context(record_har_path=str(out/'network.har'),record_har_content='embed',extra_http_headers={'X-M2-Admin-Auto-Login':'admin:admin1234'}); page=await ctx.new_page(); await page.goto(task['start_urls'][0],wait_until='domcontentloaded',timeout=60000)
  for _ in range(a.max_steps):
   try: text=(await page.locator('body').inner_text(timeout=5000))[:18000]
   except Exception: text=''
   shot=await page.screenshot(); state={'intent':task['intent'],'url':page.url,'visible_text':text,'recent_actions':hist[-6:]}; msgs=[{'role':'system','content':SYSTEM},{'role':'user','content':[{'type':'text','text':json.dumps(state,ensure_ascii=False)},{'type':'image_url','image_url':{'url':'data:image/png;base64,'+base64.b64encode(shot).decode()}}]}]
   r=client.chat.completions.create(model=MODEL,messages=msgs,tools=TOOL,tool_choice={'type':'function','function':{'name':'browser_action'}},parallel_tool_calls=False,max_tokens=900,temperature=0,extra_body={'provider':{'allow_fallbacks':False,'max_price':{'prompt':0,'completion':0}},'usage':{'include':True}}); costs.append(zero(r)); calls=r.choices[0].message.tool_calls
   if not calls: raise RuntimeError('NO_TOOL_CALL')
   x=json.loads(calls[0].function.arguments); hist.append(x); act=x['action']
   if act=='click_text': await page.get_by_text(x.get('target',''),exact=False).first.click(timeout=8000)
   elif act=='fill': await fill(page,x.get('target',''),x.get('value',''))
   elif act=='select': await page.get_by_label(x.get('target',''),exact=False).first.select_option(label=x.get('value',''))
   elif act=='press': await page.keyboard.press(x.get('key','Enter'))
   elif act=='scroll': await page.mouse.wheel(0,900)
   elif act=='wait': await page.wait_for_timeout(1000)
   elif act=='fail': result={'task_type':'NAVIGATE','status':'UNKNOWN_ERROR','retrieved_data':None,'error_details':x.get('reason','agent_failed')}; break
   elif act=='done': result={'task_type':x.get('task_type','RETRIEVE'),'status':'SUCCESS','retrieved_data':x.get('retrieved_data'),'error_details':None}; break
   await page.wait_for_timeout(500)
  if result is None: result={'task_type':'NAVIGATE','status':'UNKNOWN_ERROR','retrieved_data':None,'error_details':'max_steps_exhausted'}
  await ctx.close(); await br.close()
 (out/'agent_response.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)); (out/'arbm_trace.json').write_text(json.dumps({'model':MODEL,'task':task,'actions':hist,'usage':costs,'zero_spend':all(Decimal(v['cost'])==0 for v in costs)},indent=2,ensure_ascii=False))
if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('--tasks',required=True); ap.add_argument('--task-id',type=int,required=True); ap.add_argument('--output',required=True); ap.add_argument('--max-steps',type=int,default=24); asyncio.run(main(ap.parse_args()))