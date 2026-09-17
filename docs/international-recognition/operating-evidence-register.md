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
| OE-20260917-016 | 2026-09-17 | Representative runtime-site coverage | Run `35225844293`, SHA `babd7ec8f653fad1cf93059913756329f28596b3`: `calendar_web`, `careerlink_web`, `reviewsphere_web` and `teamchat_web` passed Caddy routing + control-plane deep-merge. Initial `mailhub_web` and `vaultbank_web` attempts reached frontend but hit transient backend `502` before control-plane readiness. | 4/6 PASS; 2 TIMING_DIAGNOSTIC | Benchmark Integrity Owner | Retry only delayed control planes with explicit readiness gate |
| OE-20260917-017 | 2026-09-17 | Control-plane readiness correction | Targeted retry run `35226207991`, SHA `abcc0e7f4e2eaa5bd68e6200113bcfe5a2d05f24`: only `mailhub_web` and `vaultbank_web` rerun. Both waited independently for frontend and `/api/state` readiness, then passed PUT/PATCH/GET deep-merge without modifying upstream source. | PASS_2_OF_2_RETRY; REPRESENTATIVE_6_OF_6_FINAL | Benchmark Integrity Owner | Expand to full runtime-site coverage |
| OE-20260917-018 | 2026-09-17 | Runtime evidence chain | Original artifacts: mailhub `10499420050` / `sha256:1b30098f15f0342ebd68589ffcc1a4a5b55187def40e2eedfe327f615f20ba3f`; careerlink `10499350262` / `sha256:a9b9b723ba8e9f17d3b256895af05a4d80c687f4a67de0ad3ac4d5c9a74d4738`; calendar `10499140424` / `sha256:1b270286816405c28ff4cd4857cc33fa85d40adc9a65840b416d5ca15c379361`; vaultbank `10499120714` / `sha256:58b9668e7265917a9b344f91b9d507126ebe617603e401b7b0e7fafff94e202f`; teamchat `10498288845` / `sha256:0300b243702d9bbeb39a1834c3125251ded5d506eadb864ef26dfdea6837bb20`; reviewsphere `10498104311` / `sha256:640ceeb93a04a0adbb069631f20b17c949d59da4ee82f18635c367f1fa53f6f6`. Final retry artifacts: mailhub `10499720163` / `sha256:86eb59869262d480b15da98ce80cbcc979e5fa2b11ca12a04299aac5f17010b4`; vaultbank `10499590617` / `sha256:01a66d95a7c91746177d53ce5c2f87a9ecd95b3edae7c852144d751bf8c3d58c`. | CHAIN_OF_CUSTODY_RECORDED | Evidence Custodian role | Preserve before 30-day artifact expiry |

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
`OSWORLD_V21_REPRESENTATIVE_RUNTIME_COVERAGE = PASS_6_OF_6`
