"""Explicit TASK091 observed-state fixture contract for tests only."""
from __future__ import annotations
import copy

def observed_task091_state(state, *, screen, window_bbox, slide_canvas_bbox,
                           slide_size, frame_identity, owner_evidence):
    if not isinstance(state, dict):
        raise ValueError("TASK091_FIXTURE_STATE_REQUIRED")
    required=(screen,window_bbox,slide_canvas_bbox,slide_size,frame_identity,owner_evidence)
    if any(value is None for value in required):
        raise ValueError("TASK091_FIXTURE_EXPLICIT_CONTRACT_REQUIRED")
    if list(state.get("screen") or []) != list(screen):
        raise ValueError("TASK091_FIXTURE_SCREEN_MISMATCH")
    if list((state.get("window") or {}).get("bbox") or []) != list(window_bbox):
        raise ValueError("TASK091_FIXTURE_WINDOW_MISMATCH")
    if dict((state.get("deck_file") or {}).get("slide_size") or {}) != dict(slide_size):
        raise ValueError("TASK091_FIXTURE_SLIDE_SIZE_MISMATCH")
    if int(state.get("active_slide") or 0) != int(frame_identity.get("active_slide") or 0):
        raise ValueError("TASK091_FIXTURE_FRAME_IDENTITY_MISMATCH")
    window=state.get("window") or {}
    for key,state_key in (("window_id","id"),("pid","pid"),("wm_class","wm_class")):
        if key in owner_evidence and owner_evidence[key] != window.get(state_key):
            raise ValueError("TASK091_FIXTURE_OWNER_EVIDENCE_MISMATCH")
    result=copy.deepcopy(state)
    result["slide_canvas_bbox"]=list(slide_canvas_bbox)
    return result
