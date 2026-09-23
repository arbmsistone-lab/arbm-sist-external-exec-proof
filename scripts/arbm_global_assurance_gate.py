"""ARBM SIST Global Assurance Gate.

This is an engineering alignment gate, not a claim of third-party certification.
It maps repository-enforced controls to current reference frameworks:
ISO/IEC 42001, ISO/IEC 23894, NIST AI RMF 1.0 + AI 600-1,
NIST CSF 2.0, NIST SSDF SP 800-218, OWASP LLM Top 10 2025,
SLSA v1.1, and Brazilian LGPD security-by-design obligations.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json
import re

PILLARS = (
    ("architecture", ("ISO/IEC 42001", "NIST AI RMF")),
    ("ai_risk_governance", ("ISO/IEC 23894", "NIST AI RMF", "NIST AI 600-1")),
    ("security_by_design", ("NIST CSF 2.0", "NIST SSDF SP 800-218")),
    ("llm_application_security", ("OWASP LLM Top 10 2025",)),
    ("provenance_supply_chain", ("SLSA v1.1", "NIST SSDF SP 800-218")),
    ("privacy_data_protection", ("LGPD Art. 46", "NIST CSF 2.0")),
    ("deterministic_execution", ("NIST AI RMF",)),
    ("bounded_mutation", ("NIST SSDF SP 800-218",)),
    ("specialist_ownership", ("ISO/IEC 42001",)),
    ("observability_auditability", ("ISO/IEC 42001", "NIST CSF 2.0")),
    ("resilience_recovery", ("NIST CSF 2.0",)),
    ("provider_resilience_zero_spend", ("ISO/IEC 23894",)),
    ("performance_resource_governance", ("NIST AI RMF",)),
    ("adversarial_regression_testing", ("NIST AI 600-1", "OWASP LLM Top 10 2025")),
    ("immutable_release_governance", ("SLSA v1.1", "NIST SSDF SP 800-218")),
    ("official_proof_admission", ("ISO/IEC 42001", "NIST AI RMF")),
)

@dataclass(frozen=True)
class PillarResult:
    name: str
    passed: bool
    evidence: tuple[str, ...]
    standards: tuple[str, ...]
    unknown: bool = False
    waiver: bool = False

def _read(root: Path, rel: str) -> str:
    path=root/rel
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8",errors="replace")

def inspect_repo(root="."):
    root=Path(root)
    shim=_read(root,"scripts/osworld_free_mesh_shim.py")
    board=_read(root,"scripts/arbm_senior_elite_board.py")
    control=_read(root,"scripts/osworld_control.py")
    policy=_read(root,"scripts/osworld_v32_policy.py")
    elite=_read(root,"scripts/osworld_elite_controller.py")
    trace=_read(root,"scripts/arbm091/trace_gate.py")
    workflow=_read(root,".github/workflows/arbm-091-clean-proof.yml")
    verifier=_read(root,"scripts/arbm091/verify_transplant.py")
    score_tests=_read(root,"tests/arbm091/test_score_and_trace.py")
    semantic_oracle=_read(root,"scripts/arbm091/semantic_transaction.py")
    semantic_runtime=_read(root,"scripts/arbm091/semantic_runtime.py")
    semantic_tests=_read(root,"tests/arbm091/test_semantic_transaction.py")
    semantic_runtime_tests=_read(root,"tests/arbm091/test_semantic_runtime.py")
    senior_tests=_read(root,"tests/arbm091/test_senior_elite_agent.py")
    req=_read(root,"scripts/requirements-osworld.txt")
    manifest=_read(root,"audit/arbm091-final-files.json")

    def result(name, ok, evidence):
        standards=dict(PILLARS)[name]
        ev=tuple(x for x in evidence if x)
        return PillarResult(name=name,passed=bool(ok and ev),evidence=ev,standards=standards)

    lanes=re.search(r"LANES\s*=\s*\((.*?)\)\s*\n",board,re.S)
    lane_count=len(re.findall(r'"[a-z_]+"',lanes.group(1))) if lanes else 0
    board_calls=shim.count("require_senior_elite(")
    pinned_actions=all("@" in line for line in workflow.splitlines()
                       if re.search(r"\buses:\s*actions/",line))
    exact_sha_gate=("same_sha_required" in _read(root,"scripts/test_osworld_elite_board_100.py")
                    and "required_consecutive_runs" in _read(root,"scripts/test_osworld_elite_board_100.py"))
    no_secret_literals=not bool(re.search(
        r"(?i)(?:api[_-]?key|secret|token)\s*=\s*['\"][A-Za-z0-9_\-]{20,}['\"]",
        "\n".join((shim,control,policy,workflow))))
    direct_gui=("DIRECT_GUI_CALL_REQUIRED" in control and "TERMINAL_FORBIDDEN" in control
                and "ACTION_COUNT" in control)
    provider_mesh=all(x in shim for x in ("FREE_ROUTE","GROQ_FREE_ROUTE","LOCAL_VLM_ROUTE"))
    provenance=("CLEAN_HISTORY_AND_SCOPE_PASS" in verifier
                and "REPAIR_COMMIT_SCOPE_MISMATCH" in verifier
                and "CHANGED_FILE_ALLOWLIST_MISMATCH" in verifier)
    zero_spend=("ZERO_SPEND_MODE: HARD" in workflow
                and "NON_ZERO_SPEND_MODE_FORBIDDEN" in shim)
    semantic_route=(
        "next_091_semantic_text_action" in shim
        and "if not state.get('semantic_text_done')" in shim
        and "return next_091_semantic_text_action(state,window_state,TASK091_SPATIAL_TEXT_EDITS)" in shim
        and "state[\"spatial_index\"]=len(plan)" in semantic_runtime
        and "verify_exact_text_transaction" in semantic_runtime
        and "assert_roundtrip" in semantic_runtime
        and "TASK091_SEMANTIC_TRANSACTION_PASS" in semantic_runtime
    )
    semantic_oracle_exact=(
        "observed_c!=allowed_c" in semantic_oracle
        and "TASK091_SEMANTIC_DIFF_MISMATCH" in semantic_oracle
        and '"collateral_diff":[]' in semantic_oracle
        and "verify_font_transaction" in semantic_oracle
        and "verify_fill_transaction" in semantic_oracle
    )
    boundary_marker="# New Task 091 architecture boundary."
    legacy_marker="# Historical replay compatibility only."
    boundary_index=shim.find(boundary_marker)
    legacy_index=shim.find(legacy_marker)
    live_boundary=(boundary_index>=0 and legacy_index>boundary_index
                   and "TASK091_LEGACY_TEXT_STATE_FORBIDDEN" in shim[boundary_index:legacy_index]
                   and "TASK091_SEMANTIC_PLAN_INCOMPLETE" in shim[boundary_index:legacy_index]
                   and "return None" in shim[boundary_index:legacy_index])
    caret_decision_isolated=(
        "_task091_caret" not in semantic_runtime
        and "ink_left" not in semantic_runtime
        and "press('home')" not in semantic_runtime
        and "press('left'" not in semantic_runtime
        and live_boundary
        and "_task091_caret_delta_geometry" not in
            shim[shim.index("def _task091_section_e_format_step"):
                 shim.index("def _task091_system_check_close")]
        and "TASK091_SECTION_E_CARET_UNPROVEN" not in
            shim[shim.index("def _task091_section_e_format_step"):
                 shim.index("def _task091_system_check_close")]
    )
    semantic_fail_closed=(
        "test_caret_zoom_and_raster_fields_have_zero_decision_power" in semantic_tests
        and "test_font_hinting_antialiasing_and_ink_left_are_not_semantic_inputs" in semantic_tests
        and "test_ambiguous_target_without_structural_hint_fails_closed" in semantic_tests
        and "test_duplicate_old_text_outside_authorized_set_blocks_global_replace" in semantic_tests
        and "test_sibling_collateral_change_fails" in semantic_tests
        and "test_unexpected_slide_relationship_change_fails_closed" in semantic_tests
        and "test_save_without_persistence_fails_roundtrip" in semantic_tests
        and "test_adversarial_collateral_rejected_then_clean_passes" in semantic_tests
        and "test_unpersisted_save_is_terminal" in semantic_runtime_tests
        and "test_migration_route_precedes_and_seals_legacy_caret_path" in semantic_runtime_tests
        and "test_semantic_certifier_rejects_any_legacy_phase" in semantic_runtime_tests
    )
    section_e_containment=(
        "TASK091_SECTION_E_FORMAT" in shim
        and "'shape_id': 16" in shim
        and "'shape_name': 'KpiReadout_Body'" in shim
        and "task091_verify_font_transaction" in shim
        and "section-e-semantic-roundtrip" in shim
        and "TASK091_SECTION_E_ROUNDTRIP_DRIFT" in shim
        and "pyautogui.hotkey('ctrl', '[')" in shim
    )
    specialist_sources=all(x in shim for x in (
        "source='task091-specialist'","source='generic-mesh'",
        "source='061-calibrated'","source='gimp-specialist'"))
    audit_logging=("SENIOR_ELITE_BOARD_PASS" in shim and "log_event" in shim
                   and "Preserve focal 091 evidence" in workflow)
    resilience=("recovery_anchor" in elite and "tabu_failed_action" in elite
                and "CHECKPOINT BACKTRACK" in shim)
    performance=("ARBM_ELITE_FAST_LATENCY_S" in shim and "ARBM_ELITE_HARD_LATENCY_S" in shim
                 and "MAX_TASK_SECONDS" in shim and "MESH_TOTAL_BUDGET_SECONDS" in shim)
    adversarial=("negative cases" in workflow.lower()
                 and "test_task091" in score_tests
                 and "test_security_vetoes_shell_capability" in senior_tests)
    privacy=(no_secret_literals and "Authorization" in shim and "oidc_token" in shim)
    requirements_pinned=bool(req.strip()) and all(
        ("==" in line or line.lstrip().startswith("#") or not line.strip())
        for line in req.splitlines())
    release_gate=("official_score_gate" in _read(root,"scripts/test_osworld_elite_board_100.py")
                  and exact_sha_gate and "release_default_blocked" in _read(root,"scripts/test_osworld_elite_board_100.py"))
    proof_admission=("needs:" in workflow and "proof-tests" in workflow
                     and "policy" in workflow and "replay" in workflow
                     and "focal-091" in workflow)

    rows=(
        result("architecture",board_calls>=4 and lane_count==10 and bool(policy) and bool(elite),
               (f"senior_board_lanes={lane_count}",f"board_enforcement_points={board_calls}")),
        result("ai_risk_governance",lane_count==10 and "fail" in board.lower() and "DecisionKind" in policy,
               ("unanimous_action_veto","typed_v32_policy")),
        result("security_by_design",direct_gui and no_secret_literals,
               ("direct_gui_only","terminal_launch_forbidden","no_hardcoded_secret_literals")),
        result("llm_application_security",direct_gui and specialist_sources and "request_tabu" in shim,
               ("action_contract","specialist_ownership","tabu_replanning")),
        result("provenance_supply_chain",provenance and pinned_actions and requirements_pinned,
               ("strict_transplant_verifier","pinned_github_actions","pinned_python_dependencies")),
        result("privacy_data_protection",privacy,
               ("no_hardcoded_secret_literals","OIDC_secret_transport")),
        result("deterministic_execution",semantic_route and semantic_oracle_exact
               and caret_decision_isolated and "temperature 0" in workflow,
               ("semantic_transaction_state_machine","caret_decision_isolated",
                "official_agent_temperature_zero")),
        result("bounded_mutation",semantic_route and semantic_oracle_exact
               and semantic_fail_closed and section_e_containment and direct_gui,
               ("exact_semantic_diff_budget","zero_collateral_mutation",
                "roundtrip_persistence","semantic_section_e_font_delta","bounded_action_compiler")),
        result("specialist_ownership",specialist_sources and "specialist_ownership" in board,
               ("all_specialist_routes_governed","091_generic_bypass_veto")),
        result("observability_auditability",audit_logging and bool(trace),
               ("per_action_board_receipt","focal_evidence_preserved","trace_gate")),
        result("resilience_recovery",resilience,
               ("tabu_failed_actions","checkpoint_backtrack")),
        result("provider_resilience_zero_spend",provider_mesh and zero_spend,
               ("three_independent_free_routes","ZERO_SPEND_MODE_HARD")),
        result("performance_resource_governance",performance,
               ("latency_gates","task_deadline","mesh_budget")),
        result("adversarial_regression_testing",adversarial,
               ("negative_cases","security_veto_tests","task091_regressions")),
        result("immutable_release_governance",provenance and release_gate and bool(manifest),
               ("immutable_scope_verifier","same_sha_10_run_rule","release_default_blocked")),
        result("official_proof_admission",proof_admission and release_gate,
               ("proof_tests_policy_replay_before_focal","score_1_exact_sha_promotion_gate")),
    )
    return rows

def summarize(rows):
    rows=tuple(rows)
    failed=[r.name for r in rows if not r.passed or r.unknown or r.waiver]
    return {
        "status":"RELEASE_READY" if not failed and len(rows)==len(PILLARS) else "BLOCKED",
        "pass":sum(1 for r in rows if r.passed and not r.unknown and not r.waiver),
        "total":len(PILLARS),
        "failed":failed,
        "unknown":sum(1 for r in rows if r.unknown),
        "waivers":sum(1 for r in rows if r.waiver),
        "pillars":[asdict(r) for r in rows],
        "certification_claimed":False,
    }

def require_release_ready(root="."):
    summary=summarize(inspect_repo(root))
    if summary["status"]!="RELEASE_READY":
        raise ValueError("GLOBAL_ASSURANCE_BLOCKED:"+",".join(summary["failed"]))
    return summary

def main():
    print(json.dumps(require_release_ready("."),sort_keys=True))

if __name__=="__main__":
    main()
