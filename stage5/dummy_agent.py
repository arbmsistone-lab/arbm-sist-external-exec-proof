from __future__ import annotations
import json,sys,time

def emit(**x):
    print(json.dumps(x),flush=True)

mode=sys.argv[1]
if mode=="success":
    emit(type="step",n=1); emit(type="model_call",cost_usd=0.0); emit(type="step",n=2); emit(type="done",claim="SUCCESS")
elif mode=="steps":
    for i in range(1,8): emit(type="step",n=i); time.sleep(.02)
elif mode=="calls":
    for i in range(5): emit(type="model_call",cost_usd=0.0); time.sleep(.02)
elif mode=="paid":
    emit(type="model_call",cost_usd=0.01); emit(type="done",claim="SUCCESS")
elif mode=="timeout":
    emit(type="step",n=1); time.sleep(5)
elif mode=="environment":
    emit(type="environment_error",code="SCREENSHOT_UNAVAILABLE",evidence="capture backend returned unavailable")
elif mode=="badlog":
    print("{not-json",flush=True)
elif mode=="verification_fail":
    emit(type="step",n=1); emit(type="done",claim="SUCCESS",verifier="FAIL")
else:
    emit(type="agent_error",code="UNKNOWN_MODE")
