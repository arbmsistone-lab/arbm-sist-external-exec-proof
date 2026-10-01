from round_policy import evaluate_round

def rec(slot,status):return {"slot_id":slot,"status":status}

cases=[]
# 1 invalid slot in 5 = exactly 20%, round remains valid.
r=evaluate_round([rec("S1","INVALID"),rec("S1","PASS"),rec("S2","PASS"),rec("S3","PASS"),rec("S4","PASS"),rec("S5","PASS")],["S1","S2","S3","S4","S5"])
cases.append(("threshold_exact_20pct",r["round_invalid"] is False,r))
# 2 invalid slots in 5 = 40%, whole round invalid.
r=evaluate_round([rec("S1","INVALID"),rec("S2","INVALID"),rec("S3","PASS"),rec("S4","PASS"),rec("S5","PASS")],["S1","S2","S3","S4","S5"])
cases.append(("over_20pct_invalid",r["round_invalid"] is True,r))
# Initial invalid plus two invalid repeats is allowed by retry ceiling.
r=evaluate_round([rec("S1","INVALID"),rec("S1","INVALID"),rec("S1","INVALID"),rec("S2","PASS"),rec("S3","PASS"),rec("S4","PASS"),rec("S5","PASS")],["S1","S2","S3","S4","S5"])
cases.append(("max_two_repeats_allowed",len(r["retry_violations"])==0,r))
# Third repeat after initial invalid is forbidden.
r=evaluate_round([rec("S1","INVALID"),rec("S1","INVALID"),rec("S1","INVALID"),rec("S1","INVALID"),rec("S2","PASS"),rec("S3","PASS"),rec("S4","PASS"),rec("S5","PASS")],["S1","S2","S3","S4","S5"])
cases.append(("third_repeat_rejected",r["round_invalid"] is True and r["retry_violations"]==["S1"],r))

ok=0
for name,good,r in cases:
    ok+=int(good); print(f"{name}: {'PASS' if good else 'FAIL'} {r}")
print(f"ROUND_POLICY_CASES={ok}/{len(cases)}")
print("INVALID_THRESHOLD_GT_20_PERCENT=PASS" if cases[0][1] and cases[1][1] else "INVALID_THRESHOLD_GT_20_PERCENT=FAIL")
print("MAX_2_INVALID_REPEATS_PER_SLOT=PASS" if cases[2][1] and cases[3][1] else "MAX_2_INVALID_REPEATS_PER_SLOT=FAIL")
print("STAGE5_ROUND_POLICY_GATE=PASS" if ok==len(cases) else "STAGE5_ROUND_POLICY_GATE=FAIL")
raise SystemExit(0 if ok==len(cases) else 1)
