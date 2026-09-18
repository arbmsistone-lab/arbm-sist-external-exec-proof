# REQUIREMENT -> IMPLEMENTATION -> CONTROL -> TEST -> EVIDENCE -> RELEASE

| Requirement | Implementation / control | Test / gate | Evidence | Current state |
|---|---|---|---|---|
| ZERO_SPEND HARD | FREE-only routing + cost/admission proof + fail-closed audit | v32 policy gate | run `35330393913` | PASS |
| heavy_local = 0 | cloud-hosted KVM workflow lane | focal workflow KVM/environment checks | focal runs + workflow definition | PASS for current closure lane |
| No false green | official score gate requires exact 1.0 | `osworld_v32_gate.py` | policy tests + official run artifacts | PASS for mechanism; result 091 pending |
| Preserve evaluator integrity | before/after integrity evidence | official audit task gate | per-task evaluator-integrity evidence | REQUIRED |
| Immutable RC during proof | frozen exact SHA | branch/SHA comparison | candidate `f114c9b1...` | ACTIVE |
| Official task 091 | official evaluator, pinned OSWorld/VM | focal 091 | run `35330495483` | BLOCKED / IN PROGRESS |
| Same-SHA official 18 | fixed official task set | official-18 workflow | not yet generated | BLOCKED |
| Supply-chain identity | pinned dependencies/artifacts + SBOM/provenance | supply-chain gate | not yet generated for final RC | BLOCKED |
| Independent verification | second logical/adversarial validation | IV&V gate | not yet generated | BLOCKED |
| Production parity | SHA/build/artifact/deploy/served equality | production gate | not yet generated | BLOCKED |
| Final technical certification | all mandatory gates PASS | meta-audit + sign-off | not yet possible | BLOCKED |

No critical requirement may be marked PASS without a reproducible evidence reference tied to the exact scope/version.
