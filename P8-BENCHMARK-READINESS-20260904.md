# ARBM SIST — P8 Benchmark Readiness — 2026-09-04

Policy: QUALITY_FIRST_ZERO_SPEND_HARD. No paid or unknown-cost route is authorized. Certification and Top-3 claims remain blocked until comparable official evidence is complete.

## Current state

| Family | Frozen pin | State | Verified blocker / next gate |
|---|---|---|---|
| SWE-rebench V2 | `c71902a8cf8d2b725f63d51f199f4d3e56f68d2d` | `WAITING_FREE_CAPACITY` | Runner, OIDC, public invariant gates and immutable evidence are working. Google free routes are quota-limited/time-limited; Cloudflare free 10,000-Neuron daily allocation is exhausted. Do not rerun blindly. |
| Terminal-Bench 4 | `452bf305c6daa62fc59061d22133a7cbc7c1572e` | `READY_SOURCE_ONLY` | Frozen source locally verified: 66 tasks, uniform 28,800 s timeout, 3 GPU tasks. Full official execution needs compatible free resources; do not substitute a weaker environment. |
| SWE-Milestone 1.0.2 | `6d8b31168fd0e2ad57c0d1daa3df1556df014320` | `READY_SOURCE_DATA_IMAGES_PENDING` | Frozen source verified at `v1.0.2`; 7 quarantine configs present. Full run requires version-matched data/images and protected evaluation. |
| OSWorld V2 2026.08.08 | `d578d2d4e0dc82b43e270fdaa7fa89d9708cd154` | `READY_PUBLIC_RELEASE_GATED_INPUTS_PENDING` | Release contract verified: code/tasks/assets all `v2026.08.08`, 108 tasks. Official tasks/assets remain gated and must not be replaced with mismatched inputs. |
| SWE-fficiency | `12d32a2d6800824a7d84bdb6797b5708e7b7957f` | `BLOCKED_PRECHECK` | Policy floor is 16,384 MB RAM. Standard GitHub runner observed ~15,988–15,989 MB. Floor must not be lowered. |

## Evidence anchors

- Latest fail-closed SWE-rebench run: `33888337781`, commit `85937138436c128aa42748c2678fe9bc9fefdf35`.
- Latest immutable SWE-rebench artifact: ID `9942846325`, archive SHA-256 `f42dbd547be049fe92c2edcdd467392ba7068afe4c22dbe6df6264cf00a49875`.
- Agent evidence SHA-256: `586f3749b1fd6d8085258eb014ad580bafb6779cb5acf0779bda63b568b4d748`.
- Readiness workflows commit: `2822bc8`.
- Supabase public-invariant-gated agent: `arbm-benchmark-agent-v17`, deployment source SHA-256 `18604e63f1a8fca1dd8e95d92c4b552aa2898f89720b279121a65cf712f948c7`.

## Release claim gate

A commercial build may describe these mechanisms as implemented and tested only to the extent evidenced above. It must not claim external certification, benchmark leadership or Top-3 placement until P8 produces reproducible comparable official results and P9 independent audit is complete.
