"""Fail-closed 20-point design audit for OSWorld task 061."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def text(rel): return (ROOT/rel).read_text(encoding="utf-8")
probe=text("scripts/osworld_gimp_sample_probe.py")
style=text("scripts/osworld_gimp_style_transfer.py")
gate=text("scripts/osworld_v32_gate.py")
workflow=text(".github/workflows/osworld-v32-official-18.yml")
probe_wf=text(".github/workflows/osworld-gimp-sample-probe.yml")
checks=[
 ("A01_exact_output_name", "OUTPUT = 'IMG_7318_edited.jpg'" in probe),
 ("A02_output_absent_preexport", "OUTPUT_PREEXISTED_BEFORE_EXPORT" in probe and "output-absent-before-export.txt" in probe),
 ("A03_guest_bytes_retrieved", "env.controller.get_file(output_path)" in probe),
 ("A04_minimum_output_size", "len(data) < 1024" in probe),
 ("A05_output_sha256", "hashlib.sha256(data).hexdigest()" in probe and "exported-output.sha256" in probe),
 ("A06_chooser_visibility_proof", "EXPORTED_OUTPUT_NOT_VISIBLE_IN_CHOOSER" in probe),
 ("A07_original_overwrite_blocked", "ORIGINAL_OVERWRITE_ATTEMPT_BLOCKED" in probe and "export-original-overwrite-cancel" in style),
 ("A08_launcher_not_window", "never the GNOME dock launcher" in probe),
 ("A09_active_target_required", "active_gimp_document(tree, TARGET)" in probe),
 ("A10_active_sample_required", "active_gimp_document(tree, SAMPLE)" in probe),
 ("A11_sample_colorize_dialog", "Sample Colorize" in probe and "dialog_open" in style and "pyautogui.press('/')" in style and "pyautogui.write('/Sample Colorize'" not in style and "pyautogui.sleep(1.0); pyautogui.press('enter')" in style),
 ("A12_get_sample_colors", "Get Sample Colors" in probe and "sample-colors" in style),
 ("A13_apply_colorize", "Apply" in probe and "apply-colorize" in style),
 ("A14_close_colorize", "Close" in probe and "close-colorize" in style),
 ("A15_modal_scoped_probe_export", "dialog_control(tree,'Export Image as JPEG','Export','push-button')" in probe),
 ("A16_modal_scoped_official_export", "_dialog_button(obs,'Export Image as JPEG','Export')" in style),
 ("A17_no_global_alt_e_confirm", "pyautogui.hotkey('alt','e')" not in style and "pyautogui.hotkey('alt','e')" not in probe),
 ("A18_exact_agent_provenance_path", "/IMG_7318_edited.jpg" in gate and "AGENT_OUTPUT_PROVENANCE_UNPROVEN" in gate),
 ("A19_provenance_before_fallback_and_bytes", "first_agent_proof > first_fallback" in gate and "AGENT_OUTPUT_BYTES_DOWNLOAD_UNPROVEN" in gate),
 ("A20_cloud_cost_integrity_score_gate", all(x in workflow for x in ["ZERO_SPEND_MODE: HARD","test -c /dev/kvm","osworld_v32_integrity.py verify","osworld_v32_gate.py task","osworld_v32_gate.py aggregate"]) and "EXPORT_PROVEN" in probe_wf),
]
failed=[name for name,ok in checks if not ok]
out={"status":"PASS" if not failed else "FAIL","count":len(checks),"passed":sum(ok for _,ok in checks),"failed":failed,"checks":[{"id":n,"pass":bool(ok)} for n,ok in checks]}
print(json.dumps(out,indent=2))
if failed: raise SystemExit(1)
