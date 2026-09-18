# RISK REGISTER — ARBM SIST

Scoring model: likelihood x impact x exposure x exploitability x business criticality. Qualitative severity is provisional until the full scoring worksheet is completed.

| ID | Finding | Severity | State | Required remediation / proof |
|---|---|---|---|---|
| R-001 | Official OSWorld task 091 has not yet produced score exactly 1.0 on frozen RC | CRITICAL release blocker | OPEN | Official 1.0 + intact evidence + no fatal shim |
| R-002 | `master` and RC are materially diverged (310 commits ahead / 265 behind at baseline) | CRITICAL release blocker for production parity | OPEN | Reconcile source lineage without losing proofs; revalidate affected scope |
| R-003 | Remote endpoint OIDC allowlist references old operational branch/workflow identities, not current frozen RC branch | HIGH / potentially blocking endpoint fallback | OPEN | Define current authorized RC identity using least privilege; test negative and positive OIDC cases; revalidate endpoint-dependent lanes |
| R-004 | Final 18/18 same-SHA official benchmark not yet executed/proven | CRITICAL release blocker | BLOCKED by R-001 | Execute only after 091 PASS |
| R-005 | Final RC SBOM/provenance/signing/attestation not yet generated | HIGH release blocker | BLOCKED | Generate after immutable final RC selected |
| R-006 | Branch protection administrative enforcement not yet evidenced for final operational branch | HIGH governance blocker | OPEN | GitHub-enforced protection/ruleset evidence |
| R-007 | Formal independent IV&V and red-team closure not yet complete | CRITICAL certification blocker | BLOCKED | Independent validation after functional gates |
| R-008 | Production deployed/served version parity not yet evidenced | CRITICAL certification blocker | BLOCKED | Production identity and E2E proof |
| R-009 | Complete secret scanning / dependency SCA / CVE review for final RC not yet evidenced in this closure ledger | HIGH | OPEN | Dedicated security/supply-chain gates |
| R-010 | Performance/load/stress/soak/chaos targets for final RC not yet sealed into release evidence | HIGH | BLOCKED | Run after functional correctness gate stabilizes |

No risk is accepted merely because it is documented.
