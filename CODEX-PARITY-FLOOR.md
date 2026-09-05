# ARBM SIST — CODEX QUALITY HARD FLOOR + ZERO-SPEND HARD

Date adopted: 2026-09-05
Policy: CODEX_PARITY_HARD_FLOOR + ZERO_SPEND_HARD
Release state: BLOCKED until independently evidenced

## Objective
ARBM SIST must demonstrate coding-agent quality that is non-inferior to the dated Codex reference on comparable tasks under the same task contract, while keeping the certified base path at mandatory AI provider cost zero.

## Non-negotiable quality rule
Commercial release is blocked while demonstrated coding competence, operational reliability, security, reproducibility, or human-effort requirements are below the certified floor.

Parity is evidence-based. Marketing language, internal scores, cherry-picked tasks, hidden evaluator feedback, gold patches, solution PRs, or a single successful run never satisfy the gate.

## Zero-spend hard rule
The certified base path runs with `ZERO_SPEND_MODE=HARD` and forbids paid inference or silent paid escalation. Cost optimization may never weaken the quality floor. Optional external modes are outside this certification unless separately proven and explicitly enabled.

## Minimum critical dimensions
1. End-to-end task correctness on frozen benchmarks.
2. Repository understanding.
3. Multi-file change quality.
4. Tool and terminal execution correctness.
5. Failure recovery.
6. Long-horizon completion without operator rescue.
7. Regression avoidance and preservation of existing contracts.
8. Sandbox, approval, network and capability controls.
9. Auditability and reproducibility with immutable hashes.
10. Human-effort requirement no worse than the reference.

## Statistical guarantee gate
Parity requires same-task comparisons, frozen harness versions, raw artifacts with SHA-256, disclosed failed runs, reproducible P8 proof, independent P9 audit, at least 30 comparable samples per certified dimension, confidence level >= 95%, and a non-inferiority margin no larger than 2 percentage points.

Critical safety, integrity, benchmark-contamination, or reliability failure is an automatic NO-GO regardless of aggregate score.

## Continuous parity rule
Parity expires when the dated reference materially changes or its validity window ends. The benchmark snapshot must be refreshed and rerun before parity may continue to be claimed.

Model/provider choice is not permanent. Promotion requires benchmark, canary, security, regression, cost and reproducibility gates.

## Claim rule
Until this gate passes, claims such as "equal to Codex", "better than Codex", "Top 3", or equivalent remain NOT AUTHORIZED. Superiority claims require a separate contemporary statistical comparison.

## Machine enforcement
The executable gate is `codex-parity-gate.mjs`; evidence is `codex-parity-evidence.json`; reproducible P8 proof is verified by `p8-repro-proof.mjs`; evidence integrity is verified by `p9-evidence-manifest.mjs`; CI enforcement is `.github/workflows/p9-codex-parity-gate.yml`.
