"""Caret-free WPS actuator for Task 091 semantic text transactions."""
from __future__ import annotations

import copy
import hashlib
import json

from osworld_control import task091_spatial_target_proof, task091_panel_target_proof
from arbm091.semantic_transaction import (
    SemanticTransactionError,
    assert_roundtrip,
    model_sha256,
    normalize_deck,
    resolve_target,
    verify_exact_text_transaction,
    validate_transaction_contract,
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
        "deck_slide_charts":copy.deepcopy(window_state.get("deck_slide_charts",{})),
        "deck_slide_relationships":copy.deepcopy(window_state.get("deck_slide_relationships",{})),
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


def _contained_replacement(before_text, old, new):
    before_text=str(before_text or "")
    old=str(old or "")
    new=str(new or "")
    if not old or before_text==old:
        return None
    if before_text.count(old)!=1:
        raise SemanticTransactionError("TASK091_CONTAINED_REPLACE_OLD_NOT_UNIQUE")
    prefix,suffix=before_text.split(old,1)
    if not new.startswith(prefix) or (suffix and not new.endswith(suffix)):
        raise SemanticTransactionError("TASK091_CONTAINED_REPLACE_BOUNDARY_DRIFT")
    end=len(new)-len(suffix) if suffix else len(new)
    replacement=new[len(prefix):end]
    if not replacement or "\n" in replacement:
        raise SemanticTransactionError("TASK091_CONTAINED_REPLACE_VALUE_INVALID")
    return replacement


def _contained_replace_command(old, replacement):
    # WPS Presentation's native Replace preserves the matched run formatting.
    # The semantic transaction has already proven the old text is unique in the
    # exact OOXML target; post-save structural diff remains fail-closed.
    return "\n".join((
        "pyautogui.hotkey('ctrl', 'h')",
        f"pyautogui.write({str(old)!r}, interval=0.08)",
        "pyautogui.press('tab')",
        f"pyautogui.write({str(replacement)!r}, interval=0.08)",
        "pyautogui.hotkey('alt', 'a')",
        "pyautogui.press('enter')",
        "pyautogui.press('esc')",
    ))


def _mutation_command(before_text, old, new):
    replacement=_contained_replacement(before_text,old,new)
    if replacement is not None:
        return _contained_replace_command(old,replacement), "contained-native-replace"
    return _write_command(new), "whole-target-replace"


def _cover_title_lock_required(tx):
    if not isinstance(tx,dict):
        return False
    key=tuple(tx.get("target_key") or ())
    if key!=(1,"shape",6,"CoverTitle"):
        return False
    before=(tx.get("before_state") or {}).get("deck_slide_shapes",{}).get("1",[])
    row=next((x for x in before if int(x.get("id") or 0)==6 and str(x.get("name") or "")=="CoverTitle"),None)
    geom=(row or {}).get("geometry") or {}
    return geom=={"x":749808,"y":1078992,"w":5852160,"h":1234440}


def _panel_target(window_state,label):
    shot=str(window_state.get("screenshot_sha256") or "")
    source=str(window_state.get("source") or "")
    window=(window_state.get("window") or {}).get("bbox")
    controls=window_state.get("controls",[]) if isinstance(window_state,dict) else []
    if window!=WINDOW or len(shot)!=64 or not source:
        raise SemanticTransactionError("TASK091_PANEL_CONTEXT_UNPROVEN")
    matches=[]
    for row in controls if isinstance(controls,list) else []:
        if not isinstance(row,dict):
            continue
        if str(row.get("label") or "").strip().casefold()!=str(label).strip().casefold():
            continue
        if row.get("showing") is not True or row.get("enabled") is not True:
            continue
        bbox=row.get("bbox")
        if not (isinstance(bbox,list) and len(bbox)==4 and all(type(v) is int for v in bbox)):
            continue
        x,y,w,h=bbox
        if w<=0 or h<=0 or not str(row.get("role") or "").strip() or type(row.get("pid")) is not int:
            continue
        wx,wy,ww,wh=window
        cx=x+w//2; cy=y+h//2
        if not (wx <= cx < wx+ww and wy <= cy < wy+wh):
            continue
        matches.append((row,x,y,w,h,cx,cy))
    if len(matches)!=1:
        raise SemanticTransactionError(
            "TASK091_PANEL_CONTROL_" + ("AMBIGUOUS" if len(matches)>1 else "NOT_OBSERVED"))
    row,x,y,w,h,cx,cy=matches[0]
    target={
        "source":"task091-panel-canonical",
        "label":str(row.get("label") or ""),
        "role":"task091-panel-point",
        "control_role":str(row.get("role") or ""),
        "control_pid":int(row.get("pid")),
        "application":str(row.get("application") or ""),
        "x":x,"y":y,"w":w,"h":h,"cx":cx,"cy":cy,
        "window_bbox":list(window),
        "screenshot_sha256":shot,
        "source_observation_id":source,
    }
    target["proof_sha256"]=task091_panel_target_proof(target)
    return target


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
            state["spatial_index"]=len(plan)
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
            try:
                resolved=resolve_target(window_state,slide=slide,old=old,
                                        hint_x=hint_x,hint_y=hint_y)
            except SemanticTransactionError as exc:
                return _terminal(str(exc))
            state["semantic_index"]=index+1
            return {"action":"checkpoint","checkpoint":"TASK091_SEMANTIC_NOOP_PROVEN",
                    "slide":slide,"old":old,"new":new,
                    "semantic_evidence":{
                        "contract_validated":True,
                        "target_resolved":True,
                        "target_unique":True,
                        "precondition":True,
                        "mutation_authorized":False,
                        "mutation":False,
                        "save":False,
                        "roundtrip":True,
                        "structural_diff":True,
                        "diff_budget_exact":True,
                        "no_collateral_mutation":True,
                        "semantic_result":True,
                        "target_key":list(resolved["key"]),
                        "before_model_sha256":resolved["model_sha256"],
                        "after_model_sha256":resolved["model_sha256"],
                    }}

        try:
            resolved=resolve_target(window_state,slide=slide,old=old,
                                    hint_x=hint_x,hint_y=hint_y)
            before=_snapshot(window_state)
            target=_signed_target(window_state,slide,resolved["row"])
        except SemanticTransactionError as exc:
            return _terminal(str(exc))

        try:
            contract=validate_transaction_contract(
                window_state,resolved["key"],old,new)
        except SemanticTransactionError as exc:
            return _terminal(str(exc))
        if contract["model_sha256"]!=resolved["model_sha256"]:
            return _terminal("TASK091_CONTRACT_MODEL_DRIFT")
        state["semantic_tx"]={
            "stage":"select-issued",
            "index":index,"slide":int(slide),"old":str(old),"new":str(new),
            "target_key":list(resolved["key"]),
            "before_state":before,
            "before_model_sha256":resolved["model_sha256"],
            "before_target_text":str(resolved["row"].get("text") or ""),
            "before_deck_sha256":str((window_state.get("deck_file") or {}).get("sha256") or ""),
            "contract":contract,
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
        if row is None or str(row.get("text") or "")!=str(tx.get("before_target_text") or ""):
            return _terminal("TASK091_PRECONDITION_DRIFT")
        if model_sha256(current_model)!=str(tx.get("before_model_sha256") or ""):
            return _terminal("TASK091_PRECONDITION_DRIFT")
        if _cover_title_lock_required(tx) and not tx.get("autofit_preflight_done"):
            tx["stage"]="autofit-pane-open-issued"
            tx["pre_autofit_screenshot_sha256"]=str(window_state.get("screenshot_sha256") or "")
            return {
                "action":"exec",
                "command":"\n".join((
                    "pyautogui.press('esc')",
                    "pyautogui.hotkey('shift', 'f10')",
                    "pyautogui.press('o')",
                    "pyautogui.sleep(0.8)",
                )),
                "plan":"Open the selected CoverTitle Format Object pane without mutating content so the exact AutoFit control can be grounded from fresh evidence.",
                "specialist_phase":"semantic-cover-autofit-pane-open",
            }
        try:
            command,mutation_mode=_mutation_command(
                tx.get("before_target_text"),tx.get("old"),tx.get("new"))
        except SemanticTransactionError as exc:
            return _terminal(str(exc))
        tx["stage"]="mutation-issued"
        tx["mutation_mode"]=mutation_mode
        return {
            "action":"exec",
            "command":command,
            "plan":("Use WPS native Replace for the unique contained semantic run so "
                    "the surrounding paragraph/run formatting is preserved; exact "
                    "OOXML diff verification remains fail-closed."
                    if mutation_mode=="contained-native-replace" else
                    "Replace the complete text of the structurally resolved WPS target. "
                    "No caret position is observed or inferred."),
            "specialist_phase":"semantic-text-mutation",
            "expected_change":tx["new"],
        }

    if stage=="autofit-pane-open-issued":
        current_shot=str(window_state.get("screenshot_sha256") or "")
        if not current_shot or current_shot==str(tx.get("pre_autofit_screenshot_sha256") or ""):
            return _terminal("TASK091_COVERTITLE_AUTOFIT_PANE_NOT_OBSERVED")
        if row is None or tuple(row.get("geometry") or ())!=(749808,1078992,5852160,1234440):
            return _terminal("TASK091_COVERTITLE_GEOMETRY_DRIFT_BEFORE_AUTOFIT")
        window=(window_state.get("window") or {}).get("bbox")
        if window!=WINDOW:
            return _terminal("TASK091_COVERTITLE_AUTOFIT_WINDOW_DRIFT")
        tx["stage"]="autofit-text-options-issued"
        tx["autofit_pane_screenshot_sha256"]=current_shot
        try:
            target=_panel_target(window_state,"TEXT OPTIONS")
        except SemanticTransactionError as exc:
            return _terminal(str(exc))
        tx["autofit_panel_points"]={"text_options":[target["cx"],target["cy"]]}
        return {
            "action":"exec",
            "command":f"pyautogui.click({target['cx']}, {target['cy']})",
            "target":target,
            "plan":"Open TEXT OPTIONS with one signed panel-canonical pointer action; no document mutation is authorized.",
            "specialist_phase":"semantic-cover-autofit-text-options-open",
        }

    if stage=="autofit-text-options-issued":
        current_shot=str(window_state.get("screenshot_sha256") or "")
        if not current_shot or current_shot==str(tx.get("autofit_pane_screenshot_sha256") or ""):
            return _terminal("TASK091_COVERTITLE_TEXT_OPTIONS_NOT_OBSERVED")
        if row is None or tuple(row.get("geometry") or ())!=(749808,1078992,5852160,1234440):
            return _terminal("TASK091_COVERTITLE_GEOMETRY_DRIFT_DURING_AUTOFIT_NAV")
        tx["stage"]="autofit-textbox-pane-issued"
        tx["text_options_screenshot_sha256"]=current_shot
        try:
            target=_panel_target(window_state,"Text Box")
        except SemanticTransactionError as exc:
            return _terminal(str(exc))
        tx["autofit_panel_points"]["text_box"]=[target["cx"],target["cy"]]
        return {
            "action":"exec",
            "command":f"pyautogui.click({target['cx']}, {target['cy']})",
            "target":target,
            "plan":"Open Text Box with one signed panel-canonical pointer action after TEXT OPTIONS was freshly observed.",
            "specialist_phase":"semantic-cover-autofit-textbox-pane-open",
        }

    if stage=="autofit-textbox-pane-issued":
        current_shot=str(window_state.get("screenshot_sha256") or "")
        if not current_shot or current_shot==str(tx.get("text_options_screenshot_sha256") or ""):
            return _terminal("TASK091_COVERTITLE_TEXTBOX_PANE_NOT_OBSERVED")
        if row is None or tuple(row.get("geometry") or ())!=(749808,1078992,5852160,1234440):
            return _terminal("TASK091_COVERTITLE_GEOMETRY_DRIFT_DURING_AUTOFIT_NAV")
        return _terminal("TASK091_COVERTITLE_TEXTBOX_PANE_CAPTURED")

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
        contract=tx.get("contract") if isinstance(tx.get("contract"),dict) else {}
        verdict=tx.get("semantic_verdict") if isinstance(tx.get("semantic_verdict"),dict) else {}
        evidence={
            "contract_validated":contract.get("status")=="PASS",
            "target_resolved":contract.get("target_resolved") is True,
            "target_unique":contract.get("target_unique") is True,
            "precondition":contract.get("precondition") is True,
            "mutation_authorized":contract.get("mutation_authorized") is True,
            "mutation":verdict.get("changed_semantic_targets")==1,
            "save":bool(tx.get("after_deck_sha256"))
                   and tx.get("after_deck_sha256")!=tx.get("before_deck_sha256"),
            "roundtrip":roundtrip.get("roundtrip") is True,
            "structural_diff":verdict.get("structural_diff") is True,
            "diff_budget_exact":verdict.get("diff_budget_exact") is True,
            "no_collateral_mutation":verdict.get("no_collateral_mutation") is True
                                     and verdict.get("collateral_diff")==[],
            "semantic_result":verdict.get("semantic_result") is True,
            "target_key":list(key),
            "before_model_sha256":tx["before_model_sha256"],
            "after_model_sha256":tx["after_model_sha256"],
            "before_deck_sha256":tx["before_deck_sha256"],
            "after_deck_sha256":tx["after_deck_sha256"],
        }
        if not all(evidence.get(name) is True for name in (
                "contract_validated","target_resolved","target_unique","precondition",
                "mutation_authorized","mutation","save","roundtrip","structural_diff",
                "diff_budget_exact","no_collateral_mutation","semantic_result")):
            return _terminal("TASK091_SEMANTIC_EVIDENCE_DERIVATION_FAILED")
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