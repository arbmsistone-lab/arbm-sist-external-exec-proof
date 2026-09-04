# ARBM SIST — CODEX PARITY FLOOR

Date adopted: 2026-09-04
Policy: CODEX_PARITY_HARD_FLOOR + QUALITY_FIRST_ZERO_SPEND_HARD
Release state: BLOCKED until independently evidenced

## Non-negotiable rule
ARBM SIST must not be approved for commercial release while its demonstrated coding competence or operational reliability is inferior to the dated Codex reference on comparable tasks under the same public task contract.

“Parity” is evidence-based. Marketing language, internal scores, cherry-picked tasks, hidden evaluator feedback, or a single successful run do not satisfy this gate.

## Minimum critical dimensions
1. End-to-end task correctness on frozen public benchmarks.
2. Repository understanding and multi-file change quality.
3. Tool/terminal execution correctness and recovery from failures.
4. Long-horizon task completion without operator rescue.
5. Regression avoidance and preservation of existing tests/contracts.
6. Security boundaries: sandboxing, approval boundaries, network/file controls.
7. Auditability: immutable logs, hashes, runner identity, model/build identity.
8. Reproducibility across repeated runs and task offsets.
9. Fail-closed behavior when safe/free capacity is unavailable.
10. Human-effort requirement no worse than the reference for the same task class.
## Evidence gate
Approval requires a dated Codex reference, same-task or contract-equivalent comparisons, frozen harness versions, raw artifacts, SHA-256 hashes, repeated runs, failure disclosure, and P9 independent audit.

No dimension above may be waived because another dimension scores higher. Critical safety/reliability failures are automatic NO-GO.

## Commercial claim rule
Until the gate passes, allowed wording is limited to mechanisms actually evidenced. Claims such as "equal to Codex", "better than Codex", "best free coding agent", "Top 3" or equivalent are NOT AUTHORIZED.

After parity is evidenced, leadership claims still require a separate contemporary comparison against the strongest currently available free alternatives.

## Continuous parity rule
Codex parity expires when the reference materially changes. The benchmark/reference snapshot must be refreshed and rerun before a later release can continue to claim parity.