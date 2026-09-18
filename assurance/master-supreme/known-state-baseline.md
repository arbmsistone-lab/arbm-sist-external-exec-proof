# KNOWN-STATE BASELINE — ARBM SIST

Baseline timestamp context: 2026-09-18 (America/Fortaleza)
Repository: `arbmsistone-lab/arbm-sist-external-exec-proof`

## Source / branch / SHA

| Item | State |
|---|---|
| Release-candidate proof branch | `chatgpt/arbm-top3-consolidated-20260917` |
| Frozen candidate SHA | `f114c9b1833d5ae5a07af923dae548033078485d` |
| Assurance ledger branch | `chatgpt/arbm-master-supreme-assurance-20260918` |
| Default branch | `master` |
| Observed master SHA | `cf008c04e9bf01e87fca80799dfc25b1de68d888` |
| Branch relation | diverged; candidate evidence must not be represented as master production state |

## Proven on frozen candidate SHA

| Gate | Evidence | State |
|---|---|---|
| OSWorld v32 deterministic policy gate | run `35330393913` | PASS |
| Complete OSWorld regression suite | step in run `35330393913` | PASS |
| v32 deterministic regression gate | step in run `35330393913` | PASS |
| Historical v31 replay through v32 policy | step in run `35330393913` | PASS |
| ZERO_SPEND policy gate | step in run `35330393913` | PASS |
| heavy-local policy | workflow/environment design; no local heavy execution in this closure lane | PASS for this lane |
| pinned OSWorld release/task/runtime prerequisites | focal workflow stages | PASS up to current completed stages |

## Not yet proven

| Gate | State | Required evidence |
|---|---|---|
| OSWorld official task 091 = 1.0 | BLOCKED / IN PROGRESS | official evaluator result 1.0 + intact artifact + no fatal shim |
| Official 18/18 same SHA | BLOCKED | all 18 official tasks exactly 1.0 on same SHA |
| Capacity / DR on final certified SHA | BLOCKED | reproducible failover/capacity/recovery evidence |
| SBOM / provenance / release attestation for final RC | BLOCKED | generated immutable artifacts tied to final SHA |
| Independent IV&V | BLOCKED | separate validation evidence |
| Final red-team | BLOCKED | adversarial report with no release blocker |
| Meta-audit | BLOCKED | audit-of-audit completeness and version consistency |
| Production parity | BLOCKED | SOURCE SHA = BUILD = ARTIFACT = DEPLOYED = SERVED VERSION |
| Final internal certification | BLOCKED | all mandatory gates PASS |

## Evidence preservation rule

Historical evidence remains valid only when scope, version, dependencies, evaluator, environment, and control semantics remain materially compatible. A passing result from another SHA is not automatically transferable to the frozen candidate.

## Current decision

**NOT CERTIFIED.** No technical basis exists yet for 100%, TOP 3 proven, or final production closure.
