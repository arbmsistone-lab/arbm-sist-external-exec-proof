"""Task 091 semantic transaction oracle.

WPS is the actuator. This module is read-only with respect to the presentation:
it consumes the OOXML-derived observer state and proves target identity, exact
semantic diffs, persistence, and absence of collateral mutation. Pixel/caret
geometry is intentionally excluded from every decision.
"""
from __future__ import annotations

import hashlib
import json


class SemanticTransactionError(ValueError):
    pass


def _norm(value):
    return " ".join(str(value or "").replace("\u200b", "").split())


def _geometry(row):
    value=row.get("geometry") if isinstance(row,dict) else None
    if not isinstance(value,dict):
        return ()
    return tuple(int(value.get(k) or 0) for k in ("x","y","w","h"))


def target_key(slide, row):
    if not isinstance(row,dict):
        raise SemanticTransactionError("TASK091_TARGET_ROW_INVALID")
    kind=str(row.get("kind") or "")
    if kind=="table-cell":
        return (
            int(slide),kind,int(row.get("frame_id") or 0),
            int(row.get("row") if row.get("row") is not None else -1),
            int(row.get("col") if row.get("col") is not None else -1),
            str(row.get("name") or ""),
        )
    return (int(slide),kind,int(row.get("id") or 0),str(row.get("name") or ""))


def normalize_deck(window_state):
    table=window_state.get("deck_slide_shapes",{}) if isinstance(window_state,dict) else {}
    if not isinstance(table,dict) or not table:
        raise SemanticTransactionError("TASK091_OOXML_STATE_MISSING")
    result={}
    for slide_s,rows in table.items():
        try:
            slide=int(slide_s)
        except Exception as exc:
            raise SemanticTransactionError("TASK091_SLIDE_KEY_INVALID") from exc
        if not isinstance(rows,list):
            raise SemanticTransactionError("TASK091_SLIDE_SHAPES_INVALID")
        for row in rows:
            if not isinstance(row,dict):
                continue
            key=target_key(slide,row)
            if key in result:
                raise SemanticTransactionError("TASK091_STRUCTURAL_IDENTITY_DUPLICATE")
            result[key]={
                "slide":slide,
                "kind":str(row.get("kind") or ""),
                "id":int(row.get("id") or 0),
                "name":str(row.get("name") or ""),
                "frame_id":int(row.get("frame_id") or 0),
                "row":int(row.get("row") if row.get("row") is not None else -1),
                "col":int(row.get("col") if row.get("col") is not None else -1),
                "text":str(row.get("text") or ""),
                "geometry":_geometry(row),
                "font_sizes":tuple(int(v) for v in (row.get("font_sizes") or []) if isinstance(v,int)),
                "fill_rgb":str(row.get("fill_rgb") or "").upper(),
            }
    if not result:
        raise SemanticTransactionError("TASK091_OOXML_STATE_EMPTY")
    return result


def model_sha256(model):
    payload=json.dumps(
        [[list(key),value] for key,value in sorted(model.items(),key=lambda item:repr(item[0]))],
        sort_keys=True,separators=(",",":"),ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _screen_center(window_state,row):
    x,y,w,h=row["geometry"]
    deck_file=window_state.get("deck_file",{}) if isinstance(window_state,dict) else {}
    slide_size=deck_file.get("slide_size",{}) if isinstance(deck_file,dict) else {}
    sw=int(slide_size.get("w") or 0); sh=int(slide_size.get("h") or 0)
    if sw<=0 or sh<=0:
        raise SemanticTransactionError("TASK091_SLIDE_SIZE_MISSING")
    # Canonical viewport is a UI-context mapping only. It never represents
    # character/caret position and never participates in semantic PASS/FAIL.
    vx,vy,vw,vh=(443,194,1413,795)
    cx=round(vx+((x+w/2)/sw)*vw)
    cy=round(vy+((y+h/2)/sh)*vh)
    return int(cx),int(cy)


def resolve_target(window_state, *, slide, old, hint_x=None, hint_y=None):
    model=normalize_deck(window_state)
    wanted=_norm(old)
    candidates=[(key,row) for key,row in model.items()
                if row["slide"]==int(slide) and _norm(row["text"])==wanted]
    if not candidates:
        raise SemanticTransactionError("TASK091_TARGET_MISSING")
    if len(candidates)==1:
        key,row=candidates[0]
        return {"key":key,"row":row,"model_sha256":model_sha256(model)}
    if hint_x is None or hint_y is None:
        raise SemanticTransactionError("TASK091_TARGET_AMBIGUOUS")
    scored=[]
    for key,row in candidates:
        cx,cy=_screen_center(window_state,row)
        scored.append(((cx-int(hint_x))**2+(cy-int(hint_y))**2,repr(key),key,row))
    scored.sort()
    if len(scored)>1 and scored[0][0]==scored[1][0]:
        raise SemanticTransactionError("TASK091_TARGET_AMBIGUOUS")
    _,_,key,row=scored[0]
    return {"key":key,"row":row,"model_sha256":model_sha256(model)}


def expected_targets_for_pair(window_state, spatial_plan, old, new):
    model=normalize_deck(window_state)
    specs=[spec for spec in spatial_plan if str(spec[3])==str(old) and str(spec[4])==str(new)]
    if not specs:
        raise SemanticTransactionError("TASK091_ALLOWED_TARGET_SET_EMPTY")
    keys=[]
    for slide,hx,hy,expected_old,expected_new in specs:
        resolved=resolve_target(window_state,slide=slide,old=expected_old,hint_x=hx,hint_y=hy)
        if resolved["key"] in keys:
            raise SemanticTransactionError("TASK091_ALLOWED_TARGET_DUPLICATE")
        keys.append(resolved["key"])
    exact_occurrences={key for key,row in model.items() if _norm(row["text"])==_norm(old)}
    return {
        "keys":tuple(keys),
        "all_exact_occurrences":tuple(sorted(exact_occurrences,key=repr)),
        "global_exact_replace_safe":set(keys)==exact_occurrences,
        "before_model_sha256":model_sha256(model),
    }


def semantic_diff(before, after):
    rows=[]
    all_keys=sorted(set(before)|set(after),key=repr)
    structural_fields=("slide","kind","id","name","frame_id","row","col","geometry","font_sizes","fill_rgb")
    for key in all_keys:
        if key not in before:
            rows.append({"key":key,"field":"target","before":None,"after":after[key]})
            continue
        if key not in after:
            rows.append({"key":key,"field":"target","before":before[key],"after":None})
            continue
        for field in structural_fields+("text",):
            if before[key].get(field)!=after[key].get(field):
                rows.append({"key":key,"field":field,
                             "before":before[key].get(field),"after":after[key].get(field)})
    return rows


def allowed_text_diff(before, target_keys, new):
    rows=[]
    for key in sorted(set(target_keys),key=repr):
        if key not in before:
            raise SemanticTransactionError("TASK091_ALLOWED_TARGET_MISSING_BEFORE")
        rows.append({"key":key,"field":"text","before":before[key]["text"],"after":str(new)})
    return rows


def verify_exact_text_transaction(before_state, after_state, target_keys, new):
    before=normalize_deck(before_state)
    after=normalize_deck(after_state)
    allowed=allowed_text_diff(before,target_keys,new)
    observed=semantic_diff(before,after)
    def canon(rows):
        return sorted(rows,key=lambda x:(repr(x["key"]),x["field"],repr(x["before"]),repr(x["after"])))
    allowed_c=canon(allowed); observed_c=canon(observed)
    if observed_c!=allowed_c:
        allowed_set={json.dumps({**r,"key":list(r["key"])},sort_keys=True,default=str) for r in allowed_c}
        collateral=[r for r in observed_c
                    if json.dumps({**r,"key":list(r["key"])},sort_keys=True,default=str) not in allowed_set]
        raise SemanticTransactionError(
            "TASK091_SEMANTIC_DIFF_MISMATCH:"+
            json.dumps({"allowed":allowed_c,"observed":observed_c,"collateral":collateral},
                       sort_keys=True,default=str))
    return {
        "status":"PASS",
        "observed_semantic_diff":observed_c,
        "allowed_semantic_diff":allowed_c,
        "changed_semantic_targets":len({tuple(r["key"]) for r in observed_c}),
        "collateral_diff":[],
        "before_model_sha256":model_sha256(before),
        "after_model_sha256":model_sha256(after),
    }


def assert_roundtrip(after_state, target_keys, new):
    model=normalize_deck(after_state)
    for key in target_keys:
        row=model.get(tuple(key))
        if row is None or str(row.get("text") or "")!=str(new):
            raise SemanticTransactionError("TASK091_ROUNDTRIP_VALUE_MISMATCH")
    return {"status":"PASS","model_sha256":model_sha256(model)}
