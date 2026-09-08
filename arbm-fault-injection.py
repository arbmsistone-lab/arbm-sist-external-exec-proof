FAULTS=("provider_timeout","provider_429","runner_crash","network_loss","lease_expired","checkpoint_corrupt")
RECOVERABLE=set(FAULTS[:-1])

def recover(state: dict, fault: str) -> dict:
    if fault not in FAULTS:
        raise ValueError("UNKNOWN_FAULT")
    if fault == "checkpoint_corrupt":
        return {**state,"status":"BLOCKED","reason":"CHECKPOINT_INTEGRITY_FAILURE","duplicate_mutation":False}
    checkpoint=state.get("checkpoint")
    if not checkpoint:
        return {**state,"status":"BLOCKED","reason":"CHECKPOINT_REQUIRED","duplicate_mutation":False}
    attempts=int(state.get("attempts",0))+1
    provider_index=(int(state.get("provider_index",0))+1)%3
    return {**state,"status":"RESUME","attempts":attempts,"provider_index":provider_index,"resume_from":checkpoint,"duplicate_mutation":False}
