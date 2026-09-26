#!/usr/bin/env python3
"""Exhaustive pre-focal gate for the closed Task 091 75+1 matrix."""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path

import osworld_free_mesh_shim as shim
from arbm091 import semantic_runtime as runtime
from arbm091 import wps_observer as observer
from arbm091.closed_matrix import TASK091_SECTION_E_FORMAT, assert_closed_matrix, matrix_rows
from arbm091.semantic_transaction import (
    SemanticTransactionError,
    assert_roundtrip,
    resolve_target,
    target_key,
    validate_transaction_contract,
    verify_exact_text_transaction,
    verify_font_transaction,
)


def _raw_row(state, key):
    slide=int(key[0])
    for row in (state.get("deck_slide_shapes",{}) or {}).get(str(slide),[]):
        try:
            if target_key(slide,row)==tuple(key):
                return row
        except Exception:
            continue
    raise ValueError("TASK091_MATRIX_RAW_TARGET_MISSING:"+repr(key))


def _handler(key, row):
    key=tuple(key)
    if key in runtime.COVERSTAT_ATOMIC_REGISTRY:
        return "coverstat-atomic"
    if key in runtime._SUMMARY_NOOP_RETRY_KEYS:
        return "summary-bounded-noop-retry"
    if key in getattr(observer,"_COVERSTAT_ATOMIC_REGISTRY",{}):
        return "observer-geometry-repair"
    if str(row.get("kind") or "")=="table-cell":
        return "table-cell-semantic"
    return "shape-semantic"


def _run_lane(baseline, lane):
    spec=(lane["slide"],lane["hint_x"],lane["hint_y"],lane["old"],lane["new"])
    resolved=resolve_target(
        baseline,slide=lane["slide"],old=lane["old"],
        hint_x=lane["hint_x"],hint_y=lane["hint_y"])
    key=tuple(resolved["key"])
    raw=_raw_row(baseline,key)
    state={"slide":lane["slide"]}
    first=runtime.next_text_action(state,baseline,(spec,))
    if first.get("action")=="terminal":
        raise ValueError("TASK091_MATRIX_RUNTIME_ENTRY_TERMINAL:"+str(first.get("reason")))
    result={
        "id":lane["id"],"slide":lane["slide"],"mode":lane["mode"],
        "target_key":list(key),"target_name":str(raw.get("name") or ""),
        "target_kind":str(raw.get("kind") or ""),
        "match_kind":resolved.get("match_kind"),
        "handler":_handler(key,raw),
        "runtime_entry":first.get("checkpoint") or first.get("specialist_phase"),
    }
    if lane["mode"]=="preserve":
        if first.get("checkpoint")!="TASK091_SEMANTIC_NOOP_PROVEN":
            raise ValueError("TASK091_MATRIX_PRESERVATION_NOT_PROVEN:"+lane["id"])
        result["contract"]="PRESERVATION_PASS"
        result["negative_collateral"]="NOT_APPLICABLE"
        return result

    contract=validate_transaction_contract(baseline,key,lane["old"],lane["new"])
    if contract.get("status")!="PASS":
        raise ValueError("TASK091_MATRIX_CONTRACT_FAIL:"+lane["id"])
    after=copy.deepcopy(baseline)
    _raw_row(after,key)["text"]=lane["new"]
    verdict=verify_exact_text_transaction(baseline,after,[key],lane["new"])
    roundtrip=assert_roundtrip(after,[key],lane["new"])
    if not verdict.get("diff_budget_exact") or not verdict.get("no_collateral_mutation"):
        raise ValueError("TASK091_MATRIX_DIFF_BUDGET_FAIL:"+lane["id"])
    if roundtrip.get("roundtrip") is not True:
        raise ValueError("TASK091_MATRIX_ROUNDTRIP_FAIL:"+lane["id"])

    bad=copy.deepcopy(after)
    bad_row=_raw_row(bad,key)
    geometry=bad_row.get("geometry") or {}
    if not all(k in geometry for k in ("x","y","w","h")):
        raise ValueError("TASK091_MATRIX_GEOMETRY_MISSING:"+lane["id"])
    bad_row["geometry"]["h"]=int(bad_row["geometry"]["h"])+1
    try:
        verify_exact_text_transaction(baseline,bad,[key],lane["new"])
    except SemanticTransactionError:
        negative="COLLATERAL_REJECTED"
    else:
        raise ValueError("TASK091_MATRIX_FALSE_GREEN_COLLATERAL:"+lane["id"])
    result["contract"]="MUTATION_PASS"
    result["negative_collateral"]=negative
    return result


def _run_section_e(baseline):
    spec=TASK091_SECTION_E_FORMAT
    rows=(baseline.get("deck_slide_shapes",{}) or {}).get(str(spec["slide"]),[])
    matches=[row for row in rows
             if int(row.get("id") or 0)==int(spec["shape_id"])
             and str(row.get("name") or "")==str(spec["shape_name"])
             and str(spec["text_fingerprint"]) in str(row.get("text") or "")]
    if len(matches)!=1:
        raise ValueError("TASK091_MATRIX_SECTION_E_TARGET_UNPROVEN")
    raw=matches[0]
    key=target_key(spec["slide"],raw)
    before_sizes=list(raw.get("font_sizes") or [])
    if not before_sizes:
        raise ValueError("TASK091_MATRIX_SECTION_E_FONT_MISSING")
    after=copy.deepcopy(baseline)
    after_row=_raw_row(after,key)
    delta=100*int(spec["font_decrements"])
    after_row["font_sizes"]=[int(v)-delta for v in before_sizes]
    verdict=verify_font_transaction(baseline,after,key,int(spec["font_decrements"]))
    state={"slide":int(spec["slide"])}
    entry=shim._task091_section_e_format_step(state,baseline)
    if entry.get("specialist_phase")!="section-e-semantic-select":
        raise ValueError("TASK091_MATRIX_SECTION_E_RUNTIME_ENTRY_FAIL:"+repr(entry))

    bad=copy.deepcopy(after)
    bad_row=_raw_row(bad,key)
    bad_row["geometry"]["h"]=int(raw["geometry"]["h"])+1
    try:
        verify_font_transaction(baseline,bad,key,int(spec["font_decrements"]))
    except SemanticTransactionError:
        negative="GEOMETRY_GROWTH_REJECTED"
    else:
        raise ValueError("TASK091_MATRIX_SECTION_E_FALSE_GREEN")
    return {
        "id":"SECTION_E","status":"PASS","target_key":list(key),
        "shape_name":spec["shape_name"],"font_decrements":spec["font_decrements"],
        "font_sizes_before":before_sizes,
        "font_sizes_after":verdict["font_sizes_after"],
        "runtime_entry":entry.get("specialist_phase"),
        "negative_geometry":negative,
    }


def evaluate(baseline_observation=None):
    summary=assert_closed_matrix()
    report={
        "status":"TASK091_CLOSED_MATRIX_PASS",
        "schema":1,
        "summary":summary,
        "baseline_observation":str(baseline_observation or ""),
        "transactions":[],
        "section_e":None,
        "blockers":[],
    }
    if baseline_observation is None:
        return report
    baseline=json.loads(Path(baseline_observation).read_text(encoding="utf-8"))
    required_slides={str(row["slide"]) for row in matrix_rows()}
    present=set((baseline.get("deck_slide_shapes") or {}).keys())
    missing=sorted(required_slides-present)
    if missing:
        report["blockers"].append({"scope":"baseline","reason":"MISSING_SLIDES","slides":missing})
    else:
        for lane in matrix_rows():
            try:
                report["transactions"].append(_run_lane(baseline,lane))
            except Exception as exc:
                report["blockers"].append({
                    "scope":lane["id"],"slide":lane["slide"],
                    "old":lane["old"],"new":lane["new"],
                    "reason":str(exc),"type":type(exc).__name__,
                })
        try:
            report["section_e"]=_run_section_e(baseline)
        except Exception as exc:
            report["blockers"].append({
                "scope":"SECTION_E","reason":str(exc),"type":type(exc).__name__,
            })
    if report["blockers"]:
        report["status"]="TASK091_CLOSED_MATRIX_FAIL"
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--baseline-observation",type=Path)
    parser.add_argument("--json-out",type=Path)
    args=parser.parse_args()
    report=evaluate(args.baseline_observation)
    rendered=json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)
    if args.json_out:
        args.json_out.write_text(rendered+"\n",encoding="utf-8")
    print(rendered)
    if report["status"]!="TASK091_CLOSED_MATRIX_PASS":
        raise SystemExit(1)
    if args.baseline_observation:
        if len(report["transactions"])!=75 or report["section_e"] is None:
            raise SystemExit("TASK091_CLOSED_MATRIX_INCOMPLETE")
        print("TASK091_CLOSED_MATRIX_75_PLUS_1=PASS")
    else:
        print("TASK091_CLOSED_MATRIX_STATIC=PASS")


if __name__=="__main__":
    main()
