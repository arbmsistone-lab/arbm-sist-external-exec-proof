import json, os, re, urllib.request
from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext

ENDPOINT=os.environ['ARBM_REMOTE_ENDPOINT'].rstrip('/')+'/v1/chat/completions'
TOKEN=os.environ['ARBM_REMOTE_TOKEN']
ACTION_RE=re.compile(r'```(?:mswea_bash_command|bash|sh|shell)\s*\n(.*?)\n```',re.S|re.I)

class ArbmRemoteAgent(BaseAgent):
    @staticmethod
    def name(): return 'arbm-remote-same-model'
    def version(self): return '11.2.0-benchmark'
    async def setup(self, environment: BaseEnvironment): return None
    def _model(self,messages):
        body={'model':'gemini-3.7-flash','messages':messages,'temperature':0,'max_tokens':1024}
        req=urllib.request.Request(ENDPOINT,data=json.dumps(body).encode(),method='POST')
        req.add_header('content-type','application/json'); req.add_header('authorization','Bearer '+TOKEN)
        with urllib.request.urlopen(req,timeout=90) as res: data=json.loads(res.read())
        return str(data['choices'][0]['message'].get('content',''))
    def _command(self,text):
        m=ACTION_RE.search(str(text)); return m.group(1).strip() if m else 'pwd && git status --short'
    async def run(self,instruction: str,environment: BaseEnvironment,context: AgentContext):
        system=('You are ARBM SIST, an autonomous coding agent. Inspect before editing. '
                'Make the smallest correct change and run focused tests. Return exactly ONE '
                'executable bash command per turn inside one ```bash block. Never invent results. '
                'When verified, return only ```bash\necho COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT\n```.')
        messages=[{'role':'system','content':system},{'role':'user','content':instruction}]
        steps=[]
        for step in range(1,26):
            text=self._model(messages); cmd=self._command(text)
            if 'COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT' in cmd:
                steps.append({'step':step,'command':'COMPLETE','returnCode':0}); break
            result=await environment.exec(cmd,timeout_sec=120)
            out=((result.stdout or '')+'\n'+(result.stderr or '')).strip()
            if len(out)>12000: out=out[:6000]+'\n...[truncated]...\n'+out[-6000:]
            steps.append({'step':step,'command':cmd[:500],'returnCode':result.return_code})
            messages.append({'role':'assistant','content':f'```bash\n{cmd}\n```'})
            messages.append({'role':'user','content':f'Command result (rc={result.return_code}):\n{out}'})
        context.cost_usd=0.0
        context.metadata={'arbmVersion':'11.2.0','model':'gemini-3.7-flash','maxSteps':25,
                          'steps':steps,'zeroSpend':True,'scaffold':'ARBM','inference':'supabase-oidc'}
