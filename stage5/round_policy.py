from __future__ import annotations
from collections import defaultdict

MAX_INVALID_REPEATS_PER_SLOT=2
ROUND_INVALID_THRESHOLD=0.20

def evaluate_round(records, expected_slots):
    by_slot=defaultdict(list)
    for r in records: by_slot[r["slot_id"]].append(r)
    retry_violations=[]
    invalid_attempts=0
    for slot,items in by_slot.items():
        invalids=sum(1 for x in items if x["status"]=="INVALID")
        invalid_attempts+=invalids
        # Initial invalid + at most two repeats = no more than 3 invalid attempts for one slot.
        if invalids>1+MAX_INVALID_REPEATS_PER_SLOT:
            retry_violations.append(slot)
    invalid_slots=sum(1 for slot in expected_slots if any(x["status"]=="INVALID" for x in by_slot.get(slot,[])))
    incidence=(invalid_slots/len(expected_slots)) if expected_slots else 0.0
    return {
      "invalid_slots":invalid_slots,
      "expected_slots":len(expected_slots),
      "invalid_incidence":incidence,
      "retry_violations":retry_violations,
      "round_invalid":bool(retry_violations or incidence>ROUND_INVALID_THRESHOLD),
      "threshold":ROUND_INVALID_THRESHOLD,
      "max_invalid_repeats_per_slot":MAX_INVALID_REPEATS_PER_SLOT,
    }
