ACTIONS=("CANCEL","PREEMPT","RESUME")
TERMINAL_STATES={"SUCCEEDED","FAILED","CANCELLED"}

def apply_control(mission: dict, action: str, actor: str) -> dict:
    if action not in ACTIONS:
        raise ValueError("CONTROL_ACTION_INVALID")
    if not actor or actor != mission.get("control_owner"):
        raise PermissionError("CONTROL_OWNER_MISMATCH")
    if mission.get("status") in TERMINAL_STATES:
        return {**mission,"control_applied":False,"reason":"MISSION_TERMINAL"}
    if action=="CANCEL":
        return {**mission,"status":"CANCELLED","control_applied":True,"lease_owner":None}
    if action=="PREEMPT":
        checkpoint=mission.get("checkpoint")
        if not checkpoint:
            return {**mission,"status":"BLOCKED","control_applied":False,"reason":"CHECKPOINT_REQUIRED"}
        return {**mission,"status":"PREEMPTED","control_applied":True,"lease_owner":None,"resume_from":checkpoint}
    if mission.get("status")!="PREEMPTED":
        return {**mission,"control_applied":False,"reason":"MISSION_NOT_PREEMPTED"}
    return {**mission,"status":"QUEUED","control_applied":True,"lease_owner":None}
