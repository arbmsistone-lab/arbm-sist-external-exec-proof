# ARBM SIST Operating Evidence Register

Status: ACTIVE
Operating evidence period start: 2026-09-17

This register starts the management-system operating period. It does not backdate controls and must only reference evidence that actually exists.

| Record ID | Date | Control / process | Evidence | Result | Owner | Next review |
|---|---|---|---|---|---|---|
| OE-20260917-001 | 2026-09-17 | Integrated policy | Integrated Management Policy approved effective 2026-09-17 | ACTIVE | Owner / Executive Management | 2027-09-17 or material change |
| OE-20260917-002 | 2026-09-17 | Scope management | Proposed integrated certification/assurance scope documented | ACTIVE_FOR_READINESS; external scope approval pending | Owner / Executive Management | On external-body response |
| OE-20260917-003 | 2026-09-17 | Control ownership | Initial control ownership assignment activated | ACTIVE; independent internal auditor pending | Owner / Executive Management | Quarterly / role change |
| OE-20260917-004 | 2026-09-17 | Risk management | 20-item integrated risk register created with no fabricated residual ratings | ACTIVE_FOR_REVIEW | Owner / Executive Management | Monthly / material change |
| OE-20260917-005 | 2026-09-17 | Evidence provenance | Auditor evidence index bound to technical anchor SHA `73772dbe40650d2e4561693db00ade48e3134ac1` | PASS | Evidence Custodian role | Monthly / new certified evidence |
| OE-20260917-006 | 2026-09-17 | Benchmark integrity | Existing world-audit run `35205586391` and focal run `35208530488` recorded with artifact digests and exact scope | PASS_FOR_HISTORICAL_RELEASE | Benchmark Integrity Owner | Before any new benchmark claim |
| OE-20260917-007 | 2026-09-17 | OSWorld release management | OSWorld V2.1 tag/commit/task/assets/website/provider-image pins captured | PASS_DESIGN | Benchmark Integrity Owner | Before execution / upstream change |
| OE-20260917-008 | 2026-09-17 | Benchmark execution authorization | V2.1 machine-readable manifest sets `full_run_authorized=false` | FAIL_CLOSED_ACTIVE | Owner / Executive Management | Only on explicit authorization |
| OE-20260917-009 | 2026-09-17 | External recognition | OSWorld, Bureau Veritas, DNV, BSI, ProMove, A-LIGN, SQS and SIG outreach initiated | CONTACTS_SENT; no certification claimed | Certification Coordinator | On response |
| OE-20260917-010 | 2026-09-17 | Spend control | External outreach explicitly states no commercial engagement/payment authorization | ZERO_SPEND_GUARD_ACTIVE | Owner / Executive Management | Before any proposal acceptance |
| OE-20260917-011 | 2026-09-17 | Internal audit | Internal-audit program defined; no audit falsely marked complete | PROGRAM_READY; independent auditor required | Owner / Executive Management | After sufficient operating evidence |
| OE-20260917-012 | 2026-09-17 | Product-quality assurance | Independent ISO/IEC 25010-oriented assessment routes opened with SQS and SIG | EXTERNAL_ASSESSMENT_PENDING | Certification Coordinator | On response |
| OE-20260917-013 | 2026-09-17 | OSWorld V2.1 self-host canary | GitHub Actions run `35225428524`, branch SHA `25dee2bda9dde66dfb56b86bce3cd5831a2974f4`; official website SHA `60c89fe6a8ed934668619d8d26132848239eb8ee`; dinogame submodule `a822adbe4ea23b48e06ae051dc14ddf5aea0b69e`; wildcard `dinogame.127.0.0.1.nip.io -> 127.0.0.1`; Caddy routing and state PUT/PATCH/GET deep-merge verified; containers torn down; zero benchmark tasks started | PASS_CANARY | Benchmark Integrity Owner | Before expanding runtime-site coverage |
| OE-20260917-014 | 2026-09-17 | Evidence retention / chain of custody | Artifact `10498659507`, `osworld-v21-selfhost-canary`, SHA256 `5a50811d97303632dc527cdf1cc7bf16ede9773def0d3f7d6bcf856130545871`; 19 evidence files; Caddy image digest `sha256:33081120c6df8613cebbdbdd4c3b8aef641e9e56c1cd3d86d04ea9651cb3cc68` | PASS | Evidence Custodian role | Before artifact expiry 2026-10-17 |
| OE-20260917-015 | 2026-09-17 | Upstream dependency security observation | Official `dinogame_web` build reported 24 npm audit findings: 2 low, 7 moderate, 13 high, 2 critical. No upstream source was modified to suppress or patch the finding. | OPEN_UPSTREAM_RISK | Security Lead / Benchmark Integrity Owner | Track upstream remediation; keep benchmark runtime isolated |

## Evidence-period rule

For management-system controls, operating-effectiveness evidence begins on or after the actual effective date shown above. Earlier technical artifacts may be used as historical technical evidence where their integrity is independently verifiable, but they do not create retroactive management-system operation.

## Record integrity rule

Each future record must contain:
- actual date;
- applicable control/process;
- real evidence identifier/location;
- factual result;
- responsible owner;
- next review or trigger.

No record may be created to imply an event occurred earlier than it actually did.

`OPERATING_EVIDENCE_PERIOD = STARTED_2026-09-17`
`OSWORLD_V21_SELFHOST_CANARY = PASS`
