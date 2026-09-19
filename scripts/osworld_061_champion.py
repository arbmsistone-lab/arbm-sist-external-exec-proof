"""Deterministic champion contract for OSWorld V2 task 061."""
OUTPUT = "IMG_7318_edited.jpg"
TARGET = "IMG_7318_original.jpg"
REFERENCE = "IMG_7328_edited.jpg"
CONTROL_SEQUENCE = (
    ("enable-subcolors", "Use subcolors", "check-box", ("alt", "e")),
    ("disable-original-intensity", "Original intensity", "check-box", ("alt", "n")),
    ("disable-hold-intensity", "Hold intensity", "check-box", ("alt", "i")),
    ("sample-colors", "Get Sample Colors", "push-button", ("alt", "s")),
    ("apply-colorize", "Apply", "push-button", ("alt", "a")),
    ("close-colorize", "Close", "push-button", ("alt", "c")),
)
ACCELERATORS={p:k for p,_l,_r,k in CONTROL_SEQUENCE}
LABELS={p:l for p,l,_r,_k in CONTROL_SEQUENCE}
ROLES={p:r for p,_l,r,_k in CONTROL_SEQUENCE}

def accelerator_command(phase):
    keys=ACCELERATORS[phase]
    return "pyautogui.hotkey(" + ", ".join(repr(k) for k in keys) + ")"

def manifest():
    return {"task":"061","output":OUTPUT,"target":TARGET,"reference":REFERENCE,
            "control_sequence":[{"phase":p,"label":l,"role":r,"accelerator":list(k)} for p,l,r,k in CONTROL_SEQUENCE],
            "invariants":["specialist_owns_transaction","accessibility_preferred","bounded_accelerator_fallback",
                          "processing_cancel_never_clicked","agent_export_precedes_evaluator_fallback",
                          "official_evaluator_unchanged","zero_spend_hard","heavy_local_zero"]}
