import asyncio
import importlib.util
import os
import sys
import types
from types import SimpleNamespace

base = types.ModuleType("harbor.agents.base")
base.BaseAgent = object
sys.modules["harbor"] = types.ModuleType("harbor")
sys.modules["harbor.agents"] = types.ModuleType("harbor.agents")
sys.modules["harbor.agents.base"] = base
spec = importlib.util.spec_from_file_location("agent", "arbm_terminal_harbor_agent.py")
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)

class Env:
    def __init__(self): self.commands = []
    async def exec(self, command, timeout_sec=120):
        self.commands.append(command)
        return SimpleNamespace(return_code=0, stdout="ok", stderr="")

async def test_run():
    calls = []
    def fake(instruction, observation, step):
        calls.append((instruction, observation, step))
        if step == 1:
            return {"ok":True,"status":"PASS","scoreable":False,"mandatory_cost_usd":0,"action":{"action":"exec","command":"pwd","summary":"inspect"}}
        return {"ok":True,"status":"PASS","scoreable":False,"mandatory_cost_usd":0,"action":{"action":"finish","command":"","summary":"done"}}
    agent._call_agent = fake
    env = Env(); context = SimpleNamespace(cost_usd=None, metadata=None)
    await agent.ARBMTerminalAgent().run("task", env, context)
    assert env.commands == ["pwd"]
    assert len(calls) == 2
    assert context.cost_usd == 0.0
    assert context.metadata["scoreable"] is False
    assert context.metadata["mandatorySpendUsd"] == 0
    assert context.metadata["remoteOnly"] is True

asyncio.run(test_run())
print('{"suite":"P3.3-TERMINAL-HARBOR-ADAPTER","pass":7,"total":7,"state":"PASS","scoreable":false}')
