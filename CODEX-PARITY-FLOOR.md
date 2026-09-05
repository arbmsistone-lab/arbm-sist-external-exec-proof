# ARBM SIST — CODEX QUALITY/COST HARD FLOOR

Date adopted: 2026-09-04
Policy: CODEX_PARITY_HARD_FLOOR + QUALITY_FIRST_COST_MIN_HARD
Release state: BLOCKED until independently evidenced

## Objective
ARBM SIST must deliver coding-agent quality that is demonstrably non-inferior to the contemporary Codex reference in every certified task class, while minimizing cost among configurations that preserve that quality floor.

The 2026-09-05 Constitution supersedes the earlier spending policy. ZERO_SPEND_MODE=HARD is mandatory; new real spending needs explicit human authorization. If free capacity cannot achieve the quality floor, the result is NO-GO, never an automatic paid fallback or reduced quality threshold.

## Non-negotiable quality rule
ARBM SIST must not be approved for commercial release while demonstrated coding competence, operational reliability, or safety is below the dated Codex reference on comparable tasks under the same task contract.

Parity is evidence-based. Marketing language, internal scores, cherry-picked tasks, hidden evaluator feedback, or a single successful run never satisfy this gate.

## Minimum critical dimensions
1. End-to-end task correctness on frozen benchmarks.
2. Repository understanding and multi-file change quality.
3. Tool/terminal execution correctness and failure recovery.
4. Long-horizon completion without operator rescue.
5. Regression avoidance and preservation of existing contracts.
6. Security boundaries and approval/network/file controls.
7. Auditability, immutable hashes, runner/model/build identity.
8. Reproducibility across repeated runs and offsets.
9. Human-effort requirement no worse than the reference.
10. Cost per resolved task lower than the Codex reference for the certified class.

## Statistical guarantee gate
Commercial parity requires same-task comparisons, frozen harness versions, raw artifacts with SHA-256, disclosed failed runs, P8 complete, P9 independent audit, at least 30 comparable samples per certified dimension, confidence level >= 95%, and a non-inferiority margin no larger than 2 percentage points.

Critical safety or reliability failure is an automatic NO-GO regardless of aggregate score.

## Cost rule
The router must select the lowest-cost authorized configuration that passes the certified quality floor. HARD mode excludes paid or unknown-cost inference. If capacity must be controlled, reduce concurrency or queue work rather than silently lowering the quality floor.

Commercial constants and launch requirements are frozen in ARBM-SIST-COMMERCIAL-POLICY.md: PRO R$1,197 includes 12 months of Continuity; R$79.90/month starts in month 13. Optional BOOST targets R$19.90/month, with managed AI COGS capped at R$7/customer/month, subject to real A/B evidence before launch. Continuity is not a premium token allowance. No automatic billing is enabled by this specification.

## Continuous parity rule
Parity expires whenever the Codex reference materially changes or the reference validity window ends. The benchmark snapshot must be refreshed and rerun before the release may continue to claim parity.

Model/provider choice is not permanent. The Evolution Engine must continuously evaluate newer, cheaper, or stronger models and only promote a configuration after benchmark, canary, security, and regression gates pass.

## Commercial claim rule
Until this gate passes, claims such as "equal to Codex", "better than Codex", "Top 3", or equivalent remain NOT AUTHORIZED. After parity is proven, superiority claims require a separate contemporary statistical comparison.

## Machine enforcement
The executable gate is `codex-parity-gate.mjs`; evidence is `codex-parity-evidence.json`; CI enforcement is `.github/workflows/p9-codex-parity-gate.yml`.
The committed evidence defaults to `BLOCKED_UNVERIFIED` and remains blocked until every critical requirement is populated and independently proven.
