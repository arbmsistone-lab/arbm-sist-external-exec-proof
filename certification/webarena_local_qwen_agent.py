import argparse, asyncio, json, os, re
from pathlib import Path
from openai import OpenAI
from playwright.async_api import async_playwright

BASE = os.environ.get('ARBM_LOCAL_BASE_URL', 'http://127.0.0.1:8080/v1')
MODEL = os.environ.get('ARBM_LOCAL_MODEL', 'qwen3-4b-local')
SHA = os.environ.get('ARBM_LOCAL_MODEL_SHA256', '')
client = OpenAI(base_url=BASE, api_key='local-zero-spend', timeout=120, max_retries=0)
SYSTEM = '''/no_think
You are a generic web benchmark agent. Work only from the current task, URL, visible text and interactive elements supplied each turn. Never use memorized benchmark answers. Return exactly one JSON object and no prose. Allowed actions: click, fill, select, press, scroll, wait, done, fail. For click/fill/select use the integer index from current interactive_elements. Do one action per turn. Use done only when the requested result is established from the page. For retrieval tasks retrieved_data must exactly match the structure requested by the task.'''

def load_task(path, tid):
    return next(x for x in json.loads(Path(path).read_text()) if int(x['task_id']) == tid)

def parse_json(text):
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.S).strip()
    try:
        return json.loads(text)
    except Exception:
        for m in reversed(list(re.finditer(r'\{', text))):
            try:
                return json.loads(text[m.start():])
            except Exception:
                pass
    raise RuntimeError('LOCAL_MODEL_NON_JSON:' + text[-500:])
async def page_state(page):
    try:
        text = (await page.locator('body').inner_text(timeout=5000))[:8000]
    except Exception:
        text = ''
    items = await page.evaluate('''() => Array.from(document.querySelectorAll('a,button,input,select,textarea,[role="button"],[role="link"]')).slice(0,140).map((e,i)=>({index:i,tag:e.tagName.toLowerCase(),text:(e.innerText||e.value||'').trim().slice(0,160),aria:(e.getAttribute('aria-label')||'').slice(0,120),placeholder:(e.getAttribute('placeholder')||'').slice(0,120),name:(e.getAttribute('name')||'').slice(0,120),type:(e.getAttribute('type')||'').slice(0,50),href:(e.getAttribute('href')||'').slice(0,180),options:e.tagName==='SELECT'?Array.from(e.options).slice(0,80).map(o=>({text:o.text,value:o.value})):undefined}))''')
    return text, items

async def apply_action(page, command):
    action = command.get('action')
    index = command.get('index')
    value = str(command.get('value', ''))
    if action in ('click', 'fill', 'select'):
        if not isinstance(index, int):
            raise RuntimeError('INDEX_REQUIRED')
        loc = page.locator('a,button,input,select,textarea,[role="button"],[role="link"]').nth(index)
        if action == 'click':
            await loc.click(timeout=10000)
        elif action == 'fill':
            await loc.fill(value, timeout=10000)
        else:
            try:
                await loc.select_option(label=value, timeout=10000)
            except Exception:
                await loc.select_option(value=value, timeout=10000)
    elif action == 'press':
        await page.keyboard.press(str(command.get('key', 'Enter')))
    elif action == 'scroll':
        await page.mouse.wheel(0, int(command.get('value', 900) or 900))
    elif action == 'wait':
        await page.wait_for_timeout(1000)
    else:
        raise RuntimeError('UNSUPPORTED_ACTION:' + str(action))
async def main(args):
    task = load_task(args.tasks, args.task_id)
    out = Path(args.output) / str(args.task_id)
    out.mkdir(parents=True, exist_ok=True)
    history, calls, result = [], 0, None
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(record_har_path=str(out / 'network.har'), record_har_content='embed', extra_http_headers={'X-M2-Admin-Auto-Login':'admin:admin1234'})
        page = await context.new_page()
        await page.goto(task['start_urls'][0], wait_until='domcontentloaded', timeout=60000)
        for _ in range(args.max_steps):
            text, items = await page_state(page)
            payload = {'task':task['intent'], 'url':page.url, 'visible_text':text, 'interactive_elements':items, 'recent_actions':history[-8:]}
            prompt = json.dumps(payload, ensure_ascii=False) + '\nReturn JSON keys action,index,value,key,task_type,retrieved_data,reason. Use null for irrelevant values.'
            response = client.chat.completions.create(model=MODEL, messages=[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}], temperature=0.1, max_tokens=500)
            calls += 1
            command = parse_json(response.choices[0].message.content or '')
            history.append(command)
            action = command.get('action')
            if action == 'done':
                result = {'task_type':command.get('task_type') or 'RETRIEVE', 'status':'SUCCESS', 'retrieved_data':command.get('retrieved_data'), 'error_details':None}
                break
            if action == 'fail':
                result = {'task_type':'NAVIGATE', 'status':'UNKNOWN_ERROR', 'retrieved_data':None, 'error_details':command.get('reason') or 'agent_failed'}
                break
            await apply_action(page, command)
            await page.wait_for_timeout(500)
        if result is None:
            result = {'task_type':'NAVIGATE', 'status':'UNKNOWN_ERROR', 'retrieved_data':None, 'error_details':'max_steps_exhausted'}
        await context.close()
        await browser.close()
    (out / 'agent_response.json').write_text(json.dumps(result, indent=2, ensure_ascii=False))
    trace = {'provider':'local-gguf','model':MODEL,'model_sha256':SHA,'external_inference_calls':0,'local_inference_calls':calls,'mandatory_cost_usd':0,'paid_fallback_used':False,'zero_spend':True,'task_id':args.task_id,'actions':history}
    (out / 'arbm_trace.json').write_text(json.dumps(trace, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tasks', required=True)
    parser.add_argument('--task-id', type=int, required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--max-steps', type=int, default=24)
    asyncio.run(main(parser.parse_args()))
