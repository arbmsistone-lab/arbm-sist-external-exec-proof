"""Caret-free WPS actuator for Task 091 semantic text transactions."""
from __future__ import annotations

import copy
import hashlib
import json

from osworld_control import task091_spatial_target_proof
from arbm091.semantic_transaction import (
    SemanticTransactionError,
    assert_roundtrip,
    model_sha256,
    normalize_deck,
    resolve_target,
    verify_exact_text_transaction,
)

SCREEN=[0,0,1920,1080]
WINDOW=[70,27,1850,1053]
VIEWPORT=[443,194,1413,795]


def _terminal(reason):
    return {"action":"terminal","reason":str(reason)}


def _foreground_sha(window_state):
    window=window_state.get("window",{}) if isinstance(window_state,dict) else {}
    payload=json.dumps(window,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest() if window else ""


def _snapshot(window_state):
    return {
        "deck_slide_shapes":copy.deepcopy(window_state.get("deck_slide_shapes",{})),
        "deck_file":copy.deepcopy(window_state.get("deck_file",{})),
    }


def _screen_center(window_state,row):
    if window_state.get("screen")!=SCREEN or (window_state.get("window") or {}).get("bbox")!=WINDOW:
        raise SemanticTransactionError("TASK091_CANONICAL_CONTEXT_UNPROVEN")
    deck_file=window_state.get("deck_file",{})
    slide_size=deck_file.get("slide_size",{}) if isinstance(deck_file,dict) else {}
    sw=int(slide_size.get("w") or 0); sh=int(slide_size.get("h") or 0)
    geom=row.get("geometry") if isinstance(row,dict) else None
    if sw<=0 or sh<=0 or not isinstance(geom,(tuple,list)) or len(geom)!=4:
        raise SemanticTransactionError("TASK091_TARGET_GEOMETRY_UNPROVEN")
    gx,gy,gw,gh=(int(v) for v in geom)
    if gx<0 or gy<0 or gw<=0 or gh<=0:
        raise SemanticTransactionError("TASK091_TARGET_GEOMETRY_INVALID")
    vx,vy,vw,vh=VIEWPORT
    cx=round(vx+((gx+gw/2)/sw)*vw)
    cy=round(vy+((gy+gh/2)/sh)*vh)
    return int(cx),int(cy)


def _signed_target(window_state,slide,row):
    cx,cy=_screen_center(window_state,row)
    deck_sha=str((window_state.get("deck_file") or {}).get("sha256") or "")
    foreground=_foreground_sha(window_state)
    if len(deck_sha)!=64 or len(foreground)!=64:
        raise SemanticTransactionError("TASK091_TARGET_DIGEST_UNPROVEN")
    target={
        "source":"task091-pptx-canonical",
        "label":str(row.get("text") or ""),
        "role":"task091-canonical-point",
        "slide":int(slide),
        "x":cx-1,"y":cy-1,"w":2,"h":2,"cx":cx,"cy":cy,
        "foreground_sha256":foreground,
        "deck_sha256":deck_sha,
    }
    target["proof_sha256"]=task091_spatial_target_proof(target)
    return target


def _nav(current,target):
    current=int(current or 1); target=int(target)
    if current==target:
        return None
    key="pagedown" if target>current else "pageup"
    return f"pyautogui.press({key!r})"


def _write_command(value):
    lines=str(value).split("\n")
    commands=["pyautogui.hotkey('ctrl', 'a')"]
    for index,line in enumerate(lines):
        if line:
            commands.append(f"pyautogui.write({line!r}, interval=0.02)")
        if index+1<len(lines):
            commands.append("pyautogui.hotkey('shift', 'enter')")
    return "\n".join(commands)


def _resolved_row_by_key(window_state,key):
    return normalize_deck(window_state).get(tuple(key))


def next_text_action(state,window_state,plan):
    """Advance exactly one semantic text transaction.

    There is deliberately no caret, ink, blink, Home, Left, or character
    position logic anywhere in this state machine.
    """
    if not isinstance(window_state,dict):
        return _terminal("TASK091_OOXML_STATE_MISSING")
    state["owned"]=True
    index=int(state.get("semantic_index") or 0)
    tx=state.get("semantic_tx")

    if not isinstance(tx,dict):
        if index>=len(plan):
            state["semantic_text_done"]=True
            return {"action":"checkpoint",
                    "checkpoint":"TASK091_SEMANTIC_TEXT_TRANSACTIONS_COMPLETE",
                    "semantic_index":index}

        slide,hint_x,hint_y,old,new=plan[index]
        current=int(state.get("slide") or 1)
        nav=_nav(current,slide)
        if nav:
            state["slide"]=current+(1 if int(slide)>current else -1)
            return {"action":"exec","command":nav,
                    "plan":f"Navigate to structural target slide {slide}.",
                    "specialist_phase":"semantic-navigate-slide"}

        if str(old)==str(new):
            state["semantic_index"]=index+1
            return {"action":"checkpoint","checkpoint":"TASK091_SEMANTIC_NOOP_PROVEN",
                    "slide":slide,"old":old,"new":new}

        try:
            resolved=resolve_target(window_state,slide=slide,old=old,
                                    hint_x=hint_x,hint_y=hint_y)
            before=_snapshot(window_state)
            target=_signed_target(window_state,slide,resolved["row"])
        except SemanticTransactionError as exc:
            return _terminal(str(exc))

        state["semantic_tx"]={
            "stage":"select-issued",
            "index":index,"slide":int(slide),"old":str(old),"new":str(new),
            "target_key":list(resolved["key"]),
            "before_state":before,
            "before_model_sha256":resolved["model_sha256"],
            "before_deck_sha256":str((window_state.get("deck_file") or {}).get("sha256") or ""),
        }
        return {
            "action":"exec",
            "command":f"pyautogui.doubleClick({target['cx']}, {target['cy']}, interval=0.08)",
            "target":target,
            "plan":"Select only the OOXML-resolved target in WPS; semantic verification, not caret geometry, authorizes the transaction.",
            "specialist_phase":"semantic-target-select",
        }

    stage=str(tx.get("stage") or "")
    key=tuple(tx.get("target_key") or ())
    try:
        current_model=normalize_deck(window_state)
    except SemanticTransactionError as exc:
        return _terminal(str(exc))
    row=current_model.get(key)

    if stage=="select-issued":
        if row is None or str(row.get("text") or "")!=str(tx.get("old") or ""):
            return _terminal("TASK091_PRECONDITION_DRIFT")
        if model_sha256(current_model)!=str(tx.get("before_model_sha256") or ""):
            return _terminal("TASK091_PRECONDITION_DRIFT")
        tx["stage"]="mutation-issued"
        return {
            "action":"exec",
            "command":_write_command(tx["new"]),
            "plan":"Replace the complete text of the structurally resolved WPS target. No caret position is observed or inferred.",
            "specialist_phase":"semantic-text-mutation",
            "expected_change":tx["new"],
        }

    if stage=="mutation-issued":
        # Finish the WPS editing operation. Disk state is verified only after save.
        tx["stage"]="commit-issued"
        return {
            "action":"exec","command":"pyautogui.press('esc')",
            "plan":"Finalize the WPS target edit before persistence.",
            "specialist_phase":"semantic-edit-finalize",
            "expected_change":tx["new"],
        }

    if stage=="commit-issued":
        tx["stage"]="save-issued"
        return {
            "action":"exec","command":"pyautogui.hotkey('ctrl', 's')",
            "plan":"Persist the isolated WPS semantic transaction.",
            "specialist_phase":"semantic-save",
            "expected_change":tx["new"],
        }

    if stage=="save-issued":
        try:
            verdict=verify_exact_text_transaction(
                tx["before_state"],window_state,[key],tx["new"])
        except SemanticTransactionError as exc:
            return _terminal(str(exc))
        current_sha=str((window_state.get("deck_file") or {}).get("sha256") or "")
        if len(current_sha)!=64 or current_sha==str(tx.get("before_deck_sha256") or ""):
            return _terminal("TASK091_SAVE_NOT_PERSISTED")
        tx["after_model_sha256"]=verdict["after_model_sha256"]
        tx["after_deck_sha256"]=current_sha
        tx["semantic_verdict"]=verdict
        tx["stage"]="roundtrip-issued"
        return {
            "action":"exec","command":"pyautogui.press('esc')",
            "plan":"Close/finalize selection so the next observer pass independently re-reads the persisted PPTX.",
            "specialist_phase":"semantic-roundtrip-reread",
        }

    if stage=="roundtrip-issued":
        try:
            roundtrip=assert_roundtrip(window_state,[key],tx["new"])
        except SemanticTransactionError as exc:
            return _terminal(str(exc))
        if roundtrip["model_sha256"]!=str(tx.get("after_model_sha256") or ""):
            return _terminal("TASK091_ROUNDTRIP_MODEL_DRIFT")
        evidence={
            "contract_validated":True,
            "target_resolved":True,
            "target_unique":True,
            "precondition":True,
            "mutation_authorized":True,
            "mutation":True,
            "save":True,
            "roundtrip":True,
            "structural_diff":True,
            "diff_budget_exact":True,
            "no_collateral_mutation":True,
            "semantic_result":True,
            "target_key":list(key),
            "before_model_sha256":tx["before_model_sha256"],
            "after_model_sha256":tx["after_model_sha256"],
            "before_deck_sha256":tx["before_deck_sha256"],
            "after_deck_sha256":tx["after_deck_sha256"],
        }
        state.setdefault("semantic_evidence",[]).append(evidence)
        state["semantic_tx"]=None
        state["semantic_index"]=int(tx["index"])+1
        return {
            "action":"checkpoint",
            "checkpoint":"TASK091_SEMANTIC_TRANSACTION_PASS",
            "slide":tx["slide"],"old":tx["old"],"new":tx["new"],
            "semantic_evidence":evidence,
        }

    return _terminal("TASK091_SEMANTIC_TRANSACTION_STATE_INVALID")
