import json, os, re, shlex, urllib.request
from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

ENDPOINT=os.environ.get('ARBM_SOVEREIGN_BACKEND','http://127.0.0.1:8088')+'/v1/chat/completions'
ACTION_RE=re.compile(r'```(?:mswea_bash_command|bash|sh|shell)\s*\n(.*?)\n```',re.S|re.I)
ABS_PATH_RE=re.compile(r'(?<![\w.-])(/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+)')
MAX_STEPS=25
VERIFY_START=19

class ArbmSovereignAgent(BaseAgent):
    @staticmethod
    def name(): return 'arbm-sovereign'
    def version(self): return '11.2.0-scaffold-v2-benchmark'
    async def setup(self, environment: BaseEnvironment): return None

    def _model(self,messages):
        payload={'model':self.model_name or 'arbm-qwen-sovereign','messages':messages,
                 'temperature':0,'max_tokens':768,'stream':False}
        req=urllib.request.Request(ENDPOINT,data=json.dumps(payload).encode(),method='POST')
        req.add_header('content-type','application/json')
        req.add_header('authorization','Bearer local-dummy-key')
        with urllib.request.urlopen(req,timeout=600) as res:
            data=json.loads(res.read())
        return str(data['choices'][0]['message'].get('content',''))

    def _command(self,text):
        m=ACTION_RE.search(str(text))
        if m: return m.group(1).strip()
        lines=[x.strip() for x in str(text).splitlines() if x.strip()]
        return lines[0] if lines else 'pwd && git status --short'

    def _required_outputs(self,instruction):
        paths=[]
        for p in ABS_PATH_RE.findall(instruction or ''):
            if p.startswith('/app/') or p.startswith('/output/') or p.startswith('/tmp/'):
                if p not in paths: paths.append(p)
        return paths[:8]

    async def _outputs_exist(self, environment, paths):
        if not paths: return True, ''
        quoted=' '.join(shlex.quote(p) for p in paths)
        cmd=f'for p in {quoted}; do test -e "$p" || {{ echo MISSING:$p; exit 3; }}; done; echo OUTPUT_CONTRACT_OK'
        result=await environment.exec(cmd,timeout_sec=30)
        text=((result.stdout or '')+'\n'+(result.stderr or '')).strip()
        return result.return_code == 0, text

    def _phase_note(self,step):
        if step < 5: return 'PHASE=PLAN: inspect requirements, environment, and existing files before creating outputs.'
        if step < VERIFY_START: return 'PHASE=BUILD: implement the complete requested artifact or code path; avoid no-op exploration.'
        return 'PHASE=VERIFY_REPAIR: stop exploring; run contract checks/tests, inspect failures, repair, and only then finish.'

    async def run(self,instruction: str,environment: BaseEnvironment,context: AgentContext):
        required_outputs=self._required_outputs(instruction)
        system=('You are ARBM SIST scaffold v2, an autonomous coding agent. Work directly in the task environment. '
                'Use a disciplined PLAN -> BUILD -> VERIFY_REPAIR cycle. Inspect before editing, satisfy every explicit '
                'output contract, make the smallest complete implementation, and verify before finishing. Return exactly '
                'ONE executable bash command per turn inside one ```bash block. Never invent files, outputs, or test results. '
                'If an output path is requested, create and validate it. Finish only after verification with '
                '```bash\necho COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n```.')
        messages=[{'role':'system','content':system},
                  {'role':'user','content':instruction+'\n\n'+self._phase_note(1)}]
        steps=[]; blocked=0; verification_seen=False
        for step in range(1,MAX_STEPS+1):
            if step == VERIFY_START:
                messages.append({'role':'user','content':self._phase_note(step)+' Run concrete checks now; repair any failure before completion.'})
            text=self._model(messages); cmd=self._command(text)
            if 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT' in cmd:
                if step < VERIFY_START:
                    blocked+=1
                    messages.extend([{'role':'assistant','content':f'```bash\n{cmd}\n```'},
                                     {'role':'user','content':'Completion blocked: verification budget is reserved. Continue implementation, then verify the task contract.'}])
                    continue
                outputs_ok,check_text=await self._outputs_exist(environment,required_outputs)
                if not outputs_ok or not verification_seen:
                    blocked+=1
                    why=check_text if not outputs_ok else 'No successful VERIFY_REPAIR command recorded yet.'
                    messages.extend([{'role':'assistant','content':f'```bash\n{cmd}\n```'},
                                     {'role':'user','content':'Completion blocked: '+why+' Run a real verification/repair command before finishing.'}])
                    continue
                steps.append({'step':step,'phase':'VERIFY_REPAIR','command':'COMPLETE','returnCode':0}); break
            phase='PLAN' if step < 5 else ('BUILD' if step < VERIFY_START else 'VERIFY_REPAIR')
            result=await environment.exec(cmd,timeout_sec=180)
            out=((result.stdout or '')+'\n'+(result.stderr or '')).strip()
            if len(out)>14000: out=out[:7000]+'\n...[truncated]...\n'+out[-7000:]
            steps.append({'step':step,'phase':phase,'command':cmd[:600],'returnCode':result.return_code})
            if phase == 'VERIFY_REPAIR' and result.return_code == 0:
                verification_seen=True
            messages.append({'role':'assistant','content':f'```bash\n{cmd}\n```'})
            feedback=f'Command result (rc={result.return_code}):\n{out}\n\n{self._phase_note(step+1)}'
            if required_outputs:
                feedback+='\nExplicit output paths detected: '+', '.join(required_outputs)
            messages.append({'role':'user','content':feedback})
        context.cost_usd=0.0
        context.metadata={'arbmVersion':'11.2.0','scaffoldVersion':'v2-benchmark',
                          'model':self.model_name or 'arbm-qwen-sovereign','maxSteps':MAX_STEPS,
                          'verifyStart':VERIFY_START,'steps':steps,'zeroSpend':True,'scaffold':'ARBM',
                          'requiredOutputs':required_outputs,'completionBlocks':blocked,
                          'verificationSeen':verification_seen}
