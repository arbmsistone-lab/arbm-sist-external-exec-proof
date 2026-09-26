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
    semantic_diff,
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
    canvas=window_state.get("slide_canvas_bbox")
    if not (isinstance(canvas,list) and len(canvas)==4 and all(type(v) is int for v in canvas)):
        raise SemanticTransactionError("TASK091_SLIDE_CANVAS_UNPROVEN")
    vx,vy,vw,vh=canvas
    if vx<0 or vy<0 or vw<=0 or vh<=0:
        raise SemanticTransactionError("TASK091_SLIDE_CANVAS_INVALID")
    if abs((vw/vh)-(sw/sh)) > 0.02:
        raise SemanticTransactionError("TASK091_SLIDE_CANVAS_ASPECT_MISMATCH")
    cx=round(vx+((gx+gw/2)/sw)*vw)
    cy=round(vy+((gy+gh/2)/sh)*vh)
    if not (vx <= cx < vx+vw and vy <= cy < vy+vh):
        raise SemanticTransactionError("TASK091_TARGET_OUTSIDE_SLIDE_CANVAS")
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
    commands=["pyautogui.press('f2')","pyautogui.hotkey('ctrl', 'a')"]
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


def _single_replace_command(old, replacement):
    # Replace only the next match in WPS, never Replace All. The saved OOXML
    # must still prove the exact target-only diff before this can pass.
    return "\n".join((
        "pyautogui.hotkey('ctrl', 'h')",
        f"pyautogui.write({str(old)!r}, interval=0.08)",
        "pyautogui.press('tab')",
        f"pyautogui.write({str(replacement)!r}, interval=0.08)",
        "pyautogui.hotkey('alt', 'n')",
        "pyautogui.hotkey('alt', 'r')",
        "pyautogui.press('esc')",
    ))


def _mutation_command(before_text, old, new):
    replacement=_contained_replacement(before_text,old,new)
    if replacement is not None:
        return _contained_replace_command(old,replacement), "contained-native-replace"
    return _write_command(new), "whole-target-replace"


_AUTOFIT_GEOMETRY_LOCKS={
    (1,"shape",6,"CoverTitle"):(749808,1078992,5852160,1234440),
    (1,"shape",7,"CoverSub"):(768096,2743200,5669280,1280160),
    (1,"shape",13,"CoverStatValue_0"):(8339327,2167128,2560320,219456),
    (1,"shape",16,"CoverStatValue_1"):(8339327,3355848,2560320,219456),
    (1,"shape",19,"CoverStatValue_2"):(8339327,4544568,2560320,219456),
}

COVERSTAT_ATOMIC_REGISTRY={
    (1,"shape",13,"CoverStatValue_0"):_AUTOFIT_GEOMETRY_LOCKS[(1,"shape",13,"CoverStatValue_0")],
    (1,"shape",16,"CoverStatValue_1"):_AUTOFIT_GEOMETRY_LOCKS[(1,"shape",16,"CoverStatValue_1")],
    (1,"shape",19,"CoverStatValue_2"):_AUTOFIT_GEOMETRY_LOCKS[(1,"shape",19,"CoverStatValue_2")],
}

_SUMMARY_NOOP_RETRY_KEYS={
    (2,"shape",15,"SummaryArr_Value"),
    (2,"shape",25,"SummaryBurn_Value"),
    (2,"shape",30,"SummaryRunway_Value"),
}


def _locked_autofit_geometry(tx):
    if not isinstance(tx,dict):
        return None
    key=tuple(tx.get("target_key") or ())
    if key in _SUMMARY_NOOP_RETRY_KEYS:
        dynamic=tx.get("retry_locked_geometry")
        if isinstance(dynamic,(list,tuple)) and len(dynamic)==4:
            return tuple(int(v) for v in dynamic)
    return _AUTOFIT_GEOMETRY_LOCKS.get(key)


def is_coverstat_atomic_contract(tx):
    """Exact registry-backed contract for panel-independent CoverStat values."""
    if not isinstance(tx,dict):
        return False
    key=tuple(tx.get("target_key") or ())
    return (
        key in COVERSTAT_ATOMIC_REGISTRY
        and str(key[3]).startswith("CoverStatValue_")
        and str(tx.get("mutation_mode") or "")=="geometry-locked-single-native-replace"
        and tx.get("panel_independent") is True
    )


def _assert_coverstat_atomic_state(window_state,tx):
    if not is_coverstat_atomic_contract(tx):
        raise SemanticTransactionError("TASK091_COVERSTAT_ATOMIC_CONTRACT_UNPROVEN")
    key=tuple(tx.get("target_key") or ())
    raw=_raw_locked_shape(window_state,tx)
    if str(raw.get("text") or "")!=str(tx.get("new") or ""):
        raise SemanticTransactionError("TASK091_COVERSTAT_ATOMIC_TEXT_DRIFT")
    geometry=tuple(int((raw.get("geometry") or {}).get(k) or 0) for k in ("x","y","w","h"))
    if geometry!=tuple(COVERSTAT_ATOMIC_REGISTRY[key]):
        raise SemanticTransactionError("TASK091_COVERSTAT_ATOMIC_GEOMETRY_DRIFT")
    return raw


def _cover_title_lock_required(tx):
    expected=_locked_autofit_geometry(tx)
    if expected is None:
        return False
    key=tuple(tx.get("target_key") or ())
    before=(tx.get("before_state") or {}).get("deck_slide_shapes",{}).get(str(key[0]),[])
    row=next((x for x in before
              if int(x.get("id") or 0)==int(key[2])
              and str(x.get("name") or "")==str(key[3])),None)
    if key==(1,"shape",13,"CoverStatValue_0") and not str((row or {}).get("autofit_mode") or ""):
        return False
    geom=(row or {}).get("geometry") or {}
    actual=tuple(int(geom.get(k) or 0) for k in ("x","y","w","h"))
    return actual==expected


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

def _raw_locked_shape(window_state,tx):
    key=tuple(tx.get("target_key") or ()) if isinstance(tx,dict) else ()
    expected=_locked_autofit_geometry(tx)
    if expected is None or len(key)!=4:
        raise SemanticTransactionError("TASK091_AUTOFIT_LOCK_TARGET_UNPROVEN")
    rows=(window_state.get("deck_slide_shapes",{}) or {}).get(str(key[0]),[]) if isinstance(window_state,dict) else []
    matches=[row for row in rows if isinstance(row,dict)
             and int(row.get("id") or 0)==int(key[2])
             and str(row.get("name") or "")==str(key[3])]
    if len(matches)!=1:
        raise SemanticTransactionError("TASK091_AUTOFIT_LOCK_RAW_STATE_UNPROVEN")
    return matches[0]


def _summary_arr_noop_retry_scope(tx,window_state):
    """Admit one exact retry for the two proven summary-value persisted no-op targets."""
    if not isinstance(tx,dict) or int(tx.get("noop_retry_attempts") or 0)!=0:
        return False
    key=tuple(tx.get("target_key") or ())
    if key not in _SUMMARY_NOOP_RETRY_KEYS:
        return False
    before=normalize_deck(tx.get("before_state") or {})
    after=normalize_deck(window_state)
    original=before.get(key); current=after.get(key)
    if not original or not current:
        return False
    if str(current.get("text") or "")!=str(tx.get("old") or ""):
        return False
    if tuple(current.get("geometry") or ())!=tuple(original.get("geometry") or ()):
        return False
    return semantic_diff(before,after)==[]


def _cover_recovery_scope(tx,window_state):
    """Admit one retry only when a geometry-locked CoverStat has text-only drift."""
    key=tuple(tx.get("target_key") or ())
    geometry=_locked_autofit_geometry(tx)
    if (geometry is None or not str(key[3] if len(key)==4 else "").startswith("CoverStatValue_")
            or int(tx.get("recovery_attempts") or 0)!=0):
        return False
    before=normalize_deck(tx["before_state"])
    after=normalize_deck(window_state)
    original=before.get(key); current=after.get(key)
    if (not original or not current or original["geometry"]!=geometry
            or current["geometry"]!=geometry):
        return False
    try:
        raw=_raw_locked_shape(window_state,tx)
    except SemanticTransactionError:
        return False
    if (str(raw.get("autofit_mode") or "")!="DO_NOT_AUTOFIT"
            or tx.get("autofit_selection_confirmed") is not True):
        return False
    observed=semantic_diff(before,after)
    if len(observed)!=1 or observed[0]["key"]!=key or observed[0]["field"]!="text":
        return False
    wrong=str(current["text"])
    expected=str(tx.get("new") or "")
    return bool(wrong and expected and wrong not in (str(tx.get("old")),expected) and len(wrong)<=64)


def _autofit_controls(window_state):
    controls=window_state.get("controls",[]) if isinstance(window_state,dict) else []
    labels=("Do not Autofit","Shrink text on overflow","Resize shape to fit text")
    result={}
    for label in labels:
        rows=[row for row in controls if isinstance(row,dict)
              and str(row.get("label") or "").strip().casefold()==label.casefold()
              and str(row.get("role") or "")=="visual-radio"
              and row.get("showing") is True and row.get("enabled") is True]
        if len(rows)!=1:
            raise SemanticTransactionError("TASK091_AUTOFIT_RADIO_GROUP_NOT_OBSERVED")
        result[label]=rows[0]
    if sum(1 for row in result.values() if row.get("selected") is True)!=1:
        raise SemanticTransactionError("TASK091_AUTOFIT_RADIO_SELECTION_AMBIGUOUS")
    return result


def _current_autofit_group(window_state,tx):
    controls=window_state.get("controls",[]) if isinstance(window_state,dict) else []
    labels=("Do not Autofit","Shrink text on overflow","Resize shape to fit text")
    candidates=[row for row in controls if isinstance(row,dict)
                and str(row.get("label") or "").strip().casefold()
                in {label.casefold() for label in labels}]
    if not candidates:
        raise SemanticTransactionError("TASK091_AUTOFIT_CURRENT_GROUP_ABSENT")
    radios=_autofit_controls(window_state)
    source=str(window_state.get("source") or "")
    shot=str(window_state.get("screenshot_sha256") or "")
    before_shot=str((tx or {}).get("selection_before_screenshot_sha256") or "")
    if not source or len(shot)!=64 or (before_shot and shot==before_shot):
        raise SemanticTransactionError("TASK091_AUTOFIT_CURRENT_GROUP_STALE_FRAME")
    owner=None
    frame_hash=None
    expected_index={
        "Do not Autofit":0,
        "Shrink text on overflow":1,
        "Resize shape to fit text":2,
    }
    for label,row in radios.items():
        bbox=row.get("bbox")
        frame_bbox=row.get("frame_bbox")
        current_owner=(int(row.get("owner_id") or 0),int(row.get("pid") or 0),
                       str(row.get("application") or ""))
        if current_owner[0]<=0 or current_owner[1]<=0 or not current_owner[2]:
            raise SemanticTransactionError("TASK091_AUTOFIT_CURRENT_GROUP_OWNER_UNPROVEN")
        if owner is None:
            owner=current_owner
        elif current_owner!=owner:
            raise SemanticTransactionError("TASK091_AUTOFIT_CURRENT_GROUP_WRONG_OWNER")
        if not (isinstance(bbox,list) and len(bbox)==4 and all(type(v) is int for v in bbox)):
            raise SemanticTransactionError("TASK091_AUTOFIT_CURRENT_GROUP_BOUNDS_UNPROVEN")
        x,y,w,h=bbox
        if w<=0 or h<=0:
            raise SemanticTransactionError("TASK091_AUTOFIT_CURRENT_GROUP_BOUNDS_UNPROVEN")
        cx=x+w//2; cy=y+h//2
        wx,wy,ww,wh=WINDOW
        if not (wx<=cx<wx+ww and wy<=cy<wy+wh):
            raise SemanticTransactionError("TASK091_AUTOFIT_CURRENT_GROUP_BOUNDS_UNPROVEN")
        if frame_bbox!=WINDOW:
            raise SemanticTransactionError("TASK091_AUTOFIT_CURRENT_GROUP_FRAME_MISMATCH")
        fh=str(row.get("frame_visual_sha256") or "")
        if len(fh)!=64:
            raise SemanticTransactionError("TASK091_AUTOFIT_CURRENT_GROUP_FRAME_UNPROVEN")
        if frame_hash is None:
            frame_hash=fh
        elif fh!=frame_hash:
            raise SemanticTransactionError("TASK091_AUTOFIT_CURRENT_GROUP_FRAME_MISMATCH")
        if str(row.get("structural_family") or "")!="wps-autofit-radio-group-v2":
            raise SemanticTransactionError("TASK091_AUTOFIT_CURRENT_GROUP_IDENTITY_MISMATCH")
        if int(row.get("structural_index") if row.get("structural_index") is not None else -1)!=expected_index[label]:
            raise SemanticTransactionError("TASK091_AUTOFIT_CURRENT_GROUP_IDENTITY_MISMATCH")
    return radios


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
            "selection_before_screenshot_sha256":str(window_state.get("screenshot_sha256") or ""),
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
            # Registry-backed CoverStats use persisted OOXML, never the WPS
            # formatting pane, as their geometry authority.
            if key in COVERSTAT_ATOMIC_REGISTRY:
                tx["autofit_preflight_done"]=True
                tx["autofit_selection_confirmed"]=False
                tx["panel_independent"]=True
                tx["stage"]="mutation-issued"
                tx["mutation_mode"]="geometry-locked-single-native-replace"
                return {
                    "action":"exec",
                    "command":_single_replace_command(tx.get("old"),tx.get("new")),
                    "plan":"Replace the unique registered CoverStat value without opening WPS formatting controls; exact OOXML text and canonical geometry remain mandatory.",
                    "specialist_phase":"semantic-coverstat-direct-replace",
                    "expected_change":tx["new"],
                }
            controls=window_state.get("controls",[]) if isinstance(window_state,dict) else []
            labels={"do not autofit","shrink text on overflow","resize shape to fit text"}
            has_autofit_candidate=any(
                isinstance(item,dict)
                and str(item.get("label") or "").strip().casefold() in labels
                for item in controls)
            if has_autofit_candidate:
                try:
                    radios=_current_autofit_group(window_state,tx)
                    raw=_raw_locked_shape(window_state,tx)
                    target=_panel_target(window_state,"Do not Autofit")
                except SemanticTransactionError as exc:
                    return _terminal(str(exc))
                if str(raw.get("autofit_mode") or "")!="RESIZE_SHAPE_TO_FIT_TEXT":
                    return _terminal("TASK091_AUTOFIT_CURRENT_MODE_UNEXPECTED")
                if radios["Resize shape to fit text"].get("selected") is not True:
                    return _terminal("TASK091_AUTOFIT_UI_OOXML_MODE_MISMATCH")
                tx["stage"]="autofit-do-not-issued"
                tx["autofit_options_screenshot_sha256"]=str(window_state.get("screenshot_sha256") or "")
                tx["autofit_preflight_source"]="current-frame-published-group"
                return {
                    "action":"exec",
                    "command":f"pyautogui.click({target['cx']}, {target['cy']})",
                    "target":target,
                    "plan":"Use the already-published, owner-consistent current-frame AutoFit group for the selected locked shape; do not reopen the proven Text Options/Text Box path.",
                    "specialist_phase":"semantic-cover-autofit-do-not-select",
                }
            has_text_options_candidate=any(
                isinstance(item,dict)
                and str(item.get("label") or "").strip().casefold()=="text options"
                and item.get("showing") is True
                and item.get("enabled") is True
                for item in controls)
            if has_text_options_candidate:
                try:
                    target=_panel_target(window_state,"TEXT OPTIONS")
                except SemanticTransactionError as exc:
                    return _terminal(str(exc))
                tx["stage"]="autofit-text-options-issued"
                tx["autofit_pane_screenshot_sha256"]=str(window_state.get("screenshot_sha256") or "")
                tx["autofit_preflight_source"]="current-frame-text-options"
                tx["autofit_panel_points"]={"text_options":[target["cx"],target["cy"]]}
                return {
                    "action":"exec",
                    "command":f"pyautogui.click({target['cx']}, {target['cy']})",
                    "target":target,
                    "plan":"Use the already-observed current-frame TEXT OPTIONS control; do not toggle or reopen a panel that is already visible.",
                    "specialist_phase":"semantic-cover-autofit-text-options-open",
                }
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
                "plan":"Open the selected locked-shape Format Object pane only when no current-frame AutoFit group is already published.",
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
        if row is None or tuple(row.get("geometry") or ())!=tuple(_locked_autofit_geometry(tx) or ()):
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
        if row is None or tuple(row.get("geometry") or ())!=tuple(_locked_autofit_geometry(tx) or ()):
            return _terminal("TASK091_COVERTITLE_GEOMETRY_DRIFT_DURING_AUTOFIT_NAV")

        # WPS may publish the complete AutoFit radio group immediately after
        # TEXT OPTIONS, without exposing a separate Text Box tab. Accept that
        # observed shortcut only when the current-frame structural radio-group
        # contract and OOXML mode both prove it is the same locked shape.
        controls=window_state.get("controls",[]) if isinstance(window_state,dict) else []
        labels={"do not autofit","shrink text on overflow","resize shape to fit text"}
        has_autofit_candidate=any(
            isinstance(item,dict)
            and str(item.get("label") or "").strip().casefold() in labels
            for item in controls)
        if has_autofit_candidate:
            try:
                radios=_current_autofit_group(window_state,tx)
                raw=_raw_locked_shape(window_state,tx)
                target=_panel_target(window_state,"Do not Autofit")
            except SemanticTransactionError as exc:
                return _terminal(str(exc))
            if str(raw.get("autofit_mode") or "")!="RESIZE_SHAPE_TO_FIT_TEXT":
                return _terminal("TASK091_AUTOFIT_CURRENT_MODE_UNEXPECTED")
            if radios["Resize shape to fit text"].get("selected") is not True:
                return _terminal("TASK091_AUTOFIT_UI_OOXML_MODE_MISMATCH")
            tx["stage"]="autofit-do-not-issued"
            tx["autofit_options_screenshot_sha256"]=current_shot
            tx["autofit_preflight_source"]="post-text-options-published-group"
            return {
                "action":"exec",
                "command":f"pyautogui.click({target['cx']}, {target['cy']})",
                "target":target,
                "plan":"TEXT OPTIONS published the complete current-frame AutoFit group directly; select only the structurally proven Do not Autofit radio.",
                "specialist_phase":"semantic-cover-autofit-do-not-select",
            }

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
        if row is None or tuple(row.get("geometry") or ())!=tuple(_locked_autofit_geometry(tx) or ()):
            return _terminal("TASK091_COVERTITLE_GEOMETRY_DRIFT_DURING_AUTOFIT_NAV")
        try:
            target=_panel_target(window_state,"PANEL DISCLOSURE")
        except SemanticTransactionError as exc:
            return _terminal(str(exc))
        tx["stage"]="autofit-disclosure-issued"
        tx["textbox_pane_screenshot_sha256"]=current_shot
        tx["autofit_panel_points"]["disclosure"]=[target["cx"],target["cy"]]
        return {
            "action":"exec",
            "command":f"pyautogui.click({target['cx']}, {target['cy']})",
            "target":target,
            "plan":"Expand the uniquely observed WPS panel disclosure with one signed current-frame action; no AutoFit option is assumed or selected.",
            "specialist_phase":"semantic-cover-autofit-disclosure-open",
        }

    if stage=="autofit-disclosure-issued":
        current_shot=str(window_state.get("screenshot_sha256") or "")
        if not current_shot or current_shot==str(tx.get("textbox_pane_screenshot_sha256") or ""):
            return _terminal("TASK091_COVERTITLE_AUTOFIT_OPTIONS_NOT_OBSERVED")
        if row is None or tuple(row.get("geometry") or ())!=tuple(_locked_autofit_geometry(tx) or ()):
            return _terminal("TASK091_COVERTITLE_GEOMETRY_DRIFT_DURING_AUTOFIT_NAV")
        try:
            radios=_autofit_controls(window_state)
            raw=_raw_locked_shape(window_state,tx)
        except SemanticTransactionError as exc:
            return _terminal(str(exc))
        if str(raw.get("autofit_mode") or "")!="RESIZE_SHAPE_TO_FIT_TEXT":
            return _terminal("TASK091_AUTOFIT_CURRENT_MODE_UNEXPECTED")
        if radios["Resize shape to fit text"].get("selected") is not True:
            # Run 407 proved a WPS state where the exact current-frame radio
            # group already reports Do not Autofit selected while the persisted
            # OOXML still reports RESIZE_SHAPE_TO_FIT_TEXT. Treat only that
            # exact combination as an in-memory/staged selection: skip the
            # redundant click, but keep final save + OOXML + geometry proof
            # mandatory. Any other UI/OOXML disagreement remains fail-closed.
            if radios["Do not Autofit"].get("selected") is True:
                tx["autofit_selection_confirmed"]=True
                tx["autofit_preflight_done"]=True
                tx["autofit_preflight_source"]="disclosure-ui-do-not-already-staged"
                tx["autofit_ui_ooxml_staged"]=True
                if str(tx.get("before_target_text") or "")==str(tx.get("old") or ""):
                    try:
                        target=_signed_target(window_state,int(tx.get("slide") or 1),row)
                    except SemanticTransactionError as exc:
                        return _terminal(str(exc))
                    tx["stage"]="autofit-reselect-issued"
                    return {
                        "action":"exec",
                        "command":f"pyautogui.doubleClick({target['cx']}, {target['cy']}, interval=0.08)",
                        "target":target,
                        "plan":"Do not Autofit is already selected in the exact WPS radio group while OOXML is still unpersisted. Re-select only the signed target; final save must prove DO_NOT_AUTOFIT and unchanged geometry.",
                        "specialist_phase":"semantic-autofit-reselect",
                    }
                tx["stage"]="select-issued"
                return {
                    "action":"checkpoint",
                    "checkpoint":"TASK091_COVERTITLE_AUTOFIT_SELECTION_ALREADY_STAGED",
                    "autofit_selected_mode":"DO_NOT_AUTOFIT",
                    "persistence_required":True,
                }
            return _terminal("TASK091_AUTOFIT_UI_OOXML_MODE_MISMATCH")
        try:
            target=_panel_target(window_state,"Do not Autofit")
        except SemanticTransactionError as exc:
            return _terminal(str(exc))
        tx["stage"]="autofit-do-not-issued"
        tx["autofit_options_screenshot_sha256"]=current_shot
        return {
            "action":"exec",
            "command":f"pyautogui.click({target['cx']}, {target['cy']})",
            "target":target,
            "plan":"Select the uniquely observed Do not Autofit radio in the current WPS Text Box panel.",
            "specialist_phase":"semantic-cover-autofit-do-not-select",
        }

    if stage=="autofit-do-not-issued":
        current_shot=str(window_state.get("screenshot_sha256") or "")
        if not current_shot or current_shot==str(tx.get("autofit_options_screenshot_sha256") or ""):
            return _terminal("TASK091_AUTOFIT_SELECTION_NOT_OBSERVED")
        try:
            radios=_autofit_controls(window_state)
        except SemanticTransactionError as exc:
            return _terminal(str(exc))
        if radios["Do not Autofit"].get("selected") is not True:
            return _terminal("TASK091_AUTOFIT_SELECTION_NOT_CONFIRMED")
        if row is None or tuple(row.get("geometry") or ())!=tuple(_locked_autofit_geometry(tx) or ()):
            return _terminal("TASK091_COVERTITLE_GEOMETRY_DRIFT_AFTER_AUTOFIT_SELECTION")
        tx["autofit_selection_confirmed"]=True
        tx["autofit_preflight_done"]=True
        if str(tx.get("before_target_text") or "")==str(tx.get("old") or ""):
            try:
                target=_signed_target(window_state,int(tx.get("slide") or 1),row)
            except SemanticTransactionError as exc:
                return _terminal(str(exc))
            tx["stage"]="autofit-reselect-issued"
            return {
                "action":"exec",
                "command":f"pyautogui.doubleClick({target['cx']}, {target['cy']}, interval=0.08)",
                "target":target,
                "plan":"Re-select the exact whole-text target after freezing AutoFit; the preserved focal artifact proves WPS double-click selects the full short value.",
                "specialist_phase":"semantic-autofit-reselect",
            }
        tx["stage"]="select-issued"
        return {
            "action":"checkpoint",
            "checkpoint":"TASK091_COVERTITLE_AUTOFIT_SELECTION_CONFIRMED",
            "autofit_selected_mode":"DO_NOT_AUTOFIT",
        }

    if stage=="autofit-reselect-issued":
        if row is None or str(row.get("text") or "")!=str(tx.get("before_target_text") or ""):
            return _terminal("TASK091_PRECONDITION_DRIFT")
        if model_sha256(current_model)!=str(tx.get("before_model_sha256") or ""):
            return _terminal("TASK091_PRECONDITION_DRIFT")
        tx["stage"]="mutation-issued"
        if tx.get("summaryarr_retry_pending") is True and key in _SUMMARY_NOOP_RETRY_KEYS:
            tx["mutation_mode"]="summaryarr-autofit-locked-selected-shape-overwrite"
            command="\n".join((
                "pyautogui.hotkey('ctrl', 'a')",
                "pyautogui.press('backspace')",
                f"pyautogui.write({str(tx.get('new') or '')!r}, interval=0.02)",
            ))
            return {
                "action":"exec","command":command,
                "plan":f"AutoFit is now proven DO_NOT_AUTOFIT for the exact {key[3]} shape. Overwrite only its selected text; OOXML must prove exact text-only diff and identical geometry.",
                "specialist_phase": (
                    "semantic-summaryrunway-noop-retry-write"
                ),
            }
        tx["mutation_mode"]="autofit-locked-single-native-replace"
        command=_single_replace_command(tx.get("old"),tx.get("new"))
        return {
            "action":"exec",
            "command":command,
            "plan":"Replace only the next matching CoverStat value in WPS. The final OOXML diff must prove that exactly this shape changed.",
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

    if stage=="summary-noop-retry-select-issued":
        if (row is None or str(row.get("text") or "")!=str(tx.get("old") or "")
                or model_sha256(current_model)!=str(tx.get("noop_retry_model_sha256") or "")):
            return _terminal("TASK091_SUMMARYARR_RETRY_SELECTION_DRIFT")
        current_shot=str(window_state.get("screenshot_sha256") or "")
        before_shot=str(tx.get("noop_retry_selection_before_screenshot_sha256") or "")
        if len(current_shot)!=64 or (before_shot and current_shot==before_shot):
            return _terminal("TASK091_SUMMARYARR_RETRY_SELECTION_UNPROVEN")
        tx["retry_locked_geometry"]=list(row.get("geometry") or ())
        tx["summaryarr_retry_pending"]=True
        tx["stage"]="select-issued"
        return next_text_action(state,window_state,plan)

    if stage=="summary-noop-retry-mutation-issued":
        tx["stage"]="summary-noop-retry-commit-issued"
        return {"action":"exec","command":"pyautogui.press('esc')",
                "specialist_phase":"semantic-summaryarr-noop-retry-commit",
                "plan":"Finalize the one permitted SummaryArr_Value no-op recovery."}

    if stage=="summary-noop-retry-commit-issued":
        tx["stage"]="summary-noop-retry-save-issued"
        return {"action":"exec","command":"pyautogui.hotkey('ctrl', 's')",
                "specialist_phase":"semantic-summaryarr-noop-retry-save",
                "plan":"Persist the one permitted SummaryArr_Value retry."}

    if stage=="summary-noop-retry-save-issued":
        current_sha=str((window_state.get("deck_file") or {}).get("sha256") or "")
        if len(current_sha)!=64:
            return _terminal("TASK091_SUMMARYARR_RETRY_PERSISTENCE_UNPROVEN")
        if current_sha==str(tx.get("noop_retry_deck_sha256") or ""):
            observations=int(tx.get("noop_retry_save_observations") or 0)+1
            tx["noop_retry_save_observations"]=observations
            if observations>=3:
                return _terminal("TASK091_SUMMARYARR_RETRY_NOT_PERSISTED")
            return {"action":"exec","command":"pyautogui.sleep(0.25)",
                    "specialist_phase":"semantic-summaryarr-noop-retry-save-reobserve",
                    "plan":"The retry save is not visible on disk yet; re-observe the exact OOXML target without issuing any additional mutation."}
        tx["noop_retry_save_observations"]=0
        if row is None or tuple(row.get("geometry") or ())!=tuple(tx.get("retry_locked_geometry") or ()):
            return _terminal("TASK091_SUMMARYARR_RETRY_GEOMETRY_DRIFT")
        try:
            verdict=verify_exact_text_transaction(tx["before_state"],window_state,[key],tx.get("new"))
        except SemanticTransactionError as exc:
            return _terminal(str(exc))
        tx["after_model_sha256"]=verdict["after_model_sha256"]
        tx["after_deck_sha256"]=current_sha
        tx["semantic_verdict"]=verdict
        tx["stage"]="roundtrip-issued"
        return {"action":"exec","command":"pyautogui.press('esc')",
                "specialist_phase":"semantic-summaryarr-noop-retry-roundtrip",
                "plan":"Independently re-read the persisted SummaryArr_Value retry before success."}

    if stage=="recovery-select-issued":
        if (row is None or str(row.get("text") or "")!=tx.get("recovery_wrong_text")
                or model_sha256(current_model)!=tx.get("recovery_model_sha256")
                or str((window_state.get("deck_file") or {}).get("sha256") or "")!=tx.get("recovery_deck_sha256")
                or _foreground_sha(window_state)!=tx.get("recovery_foreground_sha256")
                or int(window_state.get("active_slide") or 0)!=1):
            return _terminal("TASK091_COVER_RECOVERY_SELECTION_DRIFT")
        shot=str(window_state.get("screenshot_sha256") or "")
        if len(shot)!=64 or shot==tx.get("recovery_before_screenshot_sha256"):
            return _terminal("TASK091_COVER_RECOVERY_SELECTION_UNPROVEN")
        tx["stage"]="recovery-mutation-issued"
        command=_single_replace_command(tx.get("recovery_wrong_text"),tx.get("new"))
        return {"action":"exec","command":command,
                "plan":"Replace only the next matching wrong CoverStat value; exact OOXML diff remains mandatory.",
                "specialist_phase":"semantic-cover-recovery-write","expected_change":tx.get("new")}

    if stage=="recovery-mutation-issued":
        tx["stage"]="recovery-commit-issued"
        return {"action":"exec","command":"pyautogui.press('esc')",
                "specialist_phase":"semantic-cover-recovery-commit",
                "plan":"Commit the one permitted CoverStat rewrite."}

    if stage=="recovery-commit-issued":
        tx["stage"]="recovery-save-issued"
        return {"action":"exec","command":"pyautogui.hotkey('ctrl', 's')",
                "specialist_phase":"semantic-cover-recovery-save",
                "plan":"Persist the CoverStat rewrite before an independent OOXML diff."}

    if stage=="recovery-save-issued":
        current_sha=str((window_state.get("deck_file") or {}).get("sha256") or "")
        if len(current_sha)!=64 or current_sha==tx.get("recovery_deck_sha256"):
            return _terminal("TASK091_COVER_RECOVERY_NOT_PERSISTED")
        try:
            verdict=verify_exact_text_transaction(tx["before_state"],window_state,[key],tx.get("new"))
        except SemanticTransactionError as exc:
            return _terminal(str(exc))
        if tuple(current_model[key]["geometry"])!=tuple(_locked_autofit_geometry(tx) or ()):
            return _terminal("TASK091_COVER_RECOVERY_GEOMETRY_DRIFT")
        if _cover_title_lock_required(tx):
            try:
                raw=_raw_locked_shape(window_state,tx)
            except SemanticTransactionError as exc:
                return _terminal(str(exc))
            if (tx.get("autofit_selection_confirmed") is not True
                    or str(raw.get("autofit_mode") or "")!="DO_NOT_AUTOFIT"):
                return _terminal("TASK091_COVER_RECOVERY_AUTOFIT_UNPROVEN")
            tx["autofit_persisted"]=True
        tx["after_model_sha256"]=verdict["after_model_sha256"]
        tx["after_deck_sha256"]=current_sha
        tx["semantic_verdict"]=verdict
        tx["stage"]="roundtrip-issued"
        return {"action":"exec","command":"pyautogui.press('esc')",
                "specialist_phase":"semantic-cover-recovery-roundtrip",
                "plan":"Reobserve the saved OOXML before emitting the existing semantic checkpoint."}

    if stage=="save-issued":
        try:
            verdict=verify_exact_text_transaction(
                tx["before_state"],window_state,[key],tx["new"])
        except SemanticTransactionError as exc:
            current_sha=str((window_state.get("deck_file") or {}).get("sha256") or "")
            try:
                noop_scoped=_summary_arr_noop_retry_scope(tx,window_state)
            except SemanticTransactionError:
                noop_scoped=False
            if noop_scoped and len(current_sha)==64:
                try:
                    target=_signed_target(window_state,int(key[0]),current_model[key])
                except SemanticTransactionError as target_exc:
                    return _terminal(str(target_exc))
                tx["noop_retry_attempts"]=1
                tx["noop_retry_model_sha256"]=model_sha256(current_model)
                tx["noop_retry_deck_sha256"]=current_sha
                tx["noop_retry_evidence"]={
                    "classification":("SUMMARYRUNWAY_TEXT_MUTATION_NOOP"
                                      if key==(2,"shape",30,"SummaryRunway_Value")
                                      else ("SUMMARYBURN_TEXT_MUTATION_NOOP"
                                            if key==(2,"shape",25,"SummaryBurn_Value")
                                            else "SUMMARYARR_TEXT_MUTATION_NOOP")),
                    "target_key":list(key),
                    "before_text":str(tx.get("old") or ""),
                    "after_text":str(current_model[key].get("text") or ""),
                    "before_deck_sha256":str(tx.get("before_deck_sha256") or ""),
                    "observed_deck_sha256":current_sha,
                    "semantic_diff":[],
                    "geometry":list(current_model[key].get("geometry") or ()),
                    "retry_attempts":1,
                }
                tx["stage"]="summary-noop-retry-select-issued"
                tx["noop_retry_selection_before_screenshot_sha256"]=str(window_state.get("screenshot_sha256") or "")
                return {"action":"exec",
                        "command":f"pyautogui.doubleClick({target['cx']}, {target['cy']}, interval=0.08)",
                        "target":target,
                        "specialist_phase":("semantic-summaryrunway-noop-retry-select"
                                            if key==(2,"shape",30,"SummaryRunway_Value")
                                            else ("semantic-summaryburn-noop-retry-select"
                                                  if key==(2,"shape",25,"SummaryBurn_Value")
                                                  else "semantic-summaryarr-noop-retry-select")),
                        "diagnostic":tx["noop_retry_evidence"],
                        "plan":f"Retry only {key[3]} after proving the first save produced zero semantic diff and zero geometry drift; an unchanged deck SHA is expected for a true persisted no-op."}
            try:
                scoped=_cover_recovery_scope(tx,window_state)
            except SemanticTransactionError:
                scoped=False
            if (scoped and len(current_sha)==64
                    and current_sha!=str(tx.get("before_deck_sha256") or "")):
                try:
                    target=_signed_target(window_state,1,current_model[key])
                except SemanticTransactionError as target_exc:
                    return _terminal(str(target_exc))
                tx["recovery_attempts"]=1
                tx["recovery_wrong_text"]=str(current_model[key]["text"])
                tx["recovery_model_sha256"]=model_sha256(current_model)
                tx["recovery_deck_sha256"]=current_sha
                tx["recovery_foreground_sha256"]=_foreground_sha(window_state)
                tx["recovery_before_screenshot_sha256"]=str(window_state.get("screenshot_sha256") or "")
                tx["stage"]="recovery-select-issued"
                return {"action":"exec",
                        "command":f"pyautogui.doubleClick({target['cx']}, {target['cy']}, interval=0.08)",
                        "target":target,"specialist_phase":"semantic-cover-recovery-select",
                        "plan":"Reopen only the exact CoverStat shape after proving unchanged geometry and no collateral OOXML diff."}
            return _terminal(str(exc))
        current_sha=str((window_state.get("deck_file") or {}).get("sha256") or "")
        if len(current_sha)!=64 or current_sha==str(tx.get("before_deck_sha256") or ""):
            return _terminal("TASK091_SAVE_NOT_PERSISTED")
        if _cover_title_lock_required(tx):
            if is_coverstat_atomic_contract(tx):
                try:
                    _assert_coverstat_atomic_state(window_state,tx)
                except SemanticTransactionError as exc:
                    return _terminal(str(exc))
                tx["atomic_save_verified"]=True
            else:
                try:
                    raw=_raw_locked_shape(window_state,tx)
                except SemanticTransactionError as exc:
                    return _terminal(str(exc))
                if tx.get("autofit_selection_confirmed") is not True:
                    return _terminal("TASK091_AUTOFIT_SELECTION_EVIDENCE_MISSING")
                if str(raw.get("autofit_mode") or "")!="DO_NOT_AUTOFIT":
                    return _terminal("TASK091_AUTOFIT_NOT_PERSISTED")
                if tuple(int((raw.get("geometry") or {}).get(k) or 0) for k in ("x","y","w","h"))!=tuple(_locked_autofit_geometry(tx) or ()):
                    return _terminal("TASK091_COVERTITLE_GEOMETRY_DRIFT_AFTER_SAVE")
                tx["autofit_persisted"]=True
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
        if _cover_title_lock_required(tx):
            if is_coverstat_atomic_contract(tx):
                if tx.get("atomic_save_verified") is not True:
                    return _terminal("TASK091_COVERSTAT_ATOMIC_SAVE_UNPROVEN")
                try:
                    _assert_coverstat_atomic_state(window_state,tx)
                except SemanticTransactionError as exc:
                    return _terminal(str(exc))
                tx["atomic_roundtrip_verified"]=True
            else:
                try:
                    raw=_raw_locked_shape(window_state,tx)
                except SemanticTransactionError as exc:
                    return _terminal(str(exc))
                if tx.get("autofit_persisted") is not True or str(raw.get("autofit_mode") or "")!="DO_NOT_AUTOFIT":
                    return _terminal("TASK091_AUTOFIT_ROUNDTRIP_NOT_PERSISTED")
                if tuple(int((raw.get("geometry") or {}).get(k) or 0) for k in ("x","y","w","h"))!=tuple(_locked_autofit_geometry(tx) or ()):
                    return _terminal("TASK091_COVERTITLE_GEOMETRY_DRIFT_AFTER_REOPEN")
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
