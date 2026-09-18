# THREAT MODEL — ARBM SIST RC

Method: assets -> actors -> entry points -> trust boundaries -> threats -> controls -> residual risk.

## Critical assets

1. GitHub repository, branches, workflow definitions and release SHA.
2. GitHub OIDC identity and workflow claims.
3. Provider credentials and HF gated-asset credential.
4. Official evaluator/task code and pinned benchmark artifacts.
5. Evidence artifacts, checksums, score files and audit logs.
6. Agent action contract and GUI execution boundary.
7. Remote provider responses and local VLM outputs.
8. VM image and runtime patches.

## Actors

- Authorized maintainers/operators.
- GitHub Actions runners/workflows.
- External AI providers.
- Hugging Face / GitHub / container registries.
- Malicious or compromised dependency/provider.
- Adversarial UI/document content attempting prompt injection.
- Compromised credential or workflow identity.
- Accidental operator/configuration error.

## Entry points / trust boundaries

- OIDC-authenticated `endpoint/index.ts`.
- External HTTPS calls to FREE providers.
- Hugging Face artifact downloads.
- Docker image pulls.
- GitHub Actions workflow inputs/secrets.
- UI/accessibility/screenshot content fed to models.
- Model-generated action JSON crossing into local action validation.
- Evidence upload/download and historical replay.

## Key threat/control mapping

| Threat | Existing control | Residual / next gate |
|---|---|---|
| Prompt injection from UI/document | prompts explicitly mark UI/a11y text untrusted; canonical action boundary | adversarial prompt-injection suite required |
| Command injection / hidden shell | literal `pyautogui` allowlist; canonical action parser | fuzz/mutation testing required |
| Pointer mis-grounding | screenshot/a11y provenance + canonical target proof + verifier | official 091 remains blocker |
| Paid fallback / billing drift | ZERO_SPEND HARD + per-attempt proof + fail-closed audit | provider policy/pricing drift watch required |
| Provider hallucinated output | canonical parser + local policy + independent verifier | benchmark + adversarial output testing |
| OIDC token replay/wrong workflow | issuer/audience/repository/ref/workflow checks | **branch allowlist mismatch with current RC must be remediated before remote endpoint is certified for RC** |
| Secret leakage in evidence/logs | scrub/redaction code; no-store response | independent secret scan required |
| Supply-chain substitution | pinned SHAs/digests/hash verification | SBOM + provenance + signing/attestation still blocked |
| Evaluator tampering | before/after evaluator integrity | PASS mechanism; must be present per final task artifact |
| Evidence tampering | sealed checksum manifest | immutable retention/signature policy still required |
| Retry storm / uncontrolled recovery | bounded retry/cooldown/tabu/deadline controls | stress/fault-injection required |
| Provider outage/quota exhaustion | multi-route FREE + local VLM | capacity/DR gate required |
| Branch/source drift | exact SHA evidence | **master/RC divergence is a release blocker until reconciled** |

## Fail-closed assertions

- Unknown action contract -> reject.
- Unknown cost proof -> reject response for action promotion.
- Evaluator mismatch/tamper -> fail.
- Missing evidence -> fail/block.
- Official score other than exactly 1.0 -> not PASS.
- Runtime change after RC freeze -> affected gates invalidated.

## Residual risk

No final residual-risk acceptance has been issued. All material residuals remain open until red-team, IV&V, capacity/DR, supply-chain and production-parity gates are complete.
