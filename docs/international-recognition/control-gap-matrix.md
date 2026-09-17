# International Recognition Control and Gap Matrix

Anchor SHA: `73772dbe40650d2e4561693db00ade48e3134ac1`

Legend:
- `EVIDENCE_FOUND` - objective repository/run evidence already exists.
- `PARTIAL` - some technical evidence exists but organizational records or scope evidence are incomplete.
- `NEEDS_ORG_EVIDENCE` - requires formal organizational policy/record/approval.
- `EXTERNAL_REQUIRED` - closure depends on an independent auditor, certification body, maintainer or appraisal team.

| Domain | Existing objective evidence | Status | Next evidence needed |
|---|---|---|---|
| Reproducible execution | Pinned SHA, workflow runs, artifacts and SHA256 manifests | EVIDENCE_FOUND | Preserve immutable references in audit index |
| Evaluator integrity | Pre/post evaluator integrity checks and official evaluator pinning | EVIDENCE_FOUND | Independent reviewer acceptance for external benchmark |
| Provenance | Fail-closed evidence binding, candidate SHA checks, artifact hashes | EVIDENCE_FOUND | Consolidated chain-of-custody index |
| Zero-spend engineering policy | `ZERO_SPEND_MODE=HARD`, paid fallback prohibited | EVIDENCE_FOUND | Formal management policy if included in certification scope |
| Heavy-local prohibition | GitHub-hosted execution and heavy-local=0 evidence | EVIDENCE_FOUND | Formal operating policy and exception process |
| Change control | Git SHA lineage and CI workflow definitions | PARTIAL | Formal change-management procedure, approvals and release records |
| Risk management | Technical fail-closed gates and RCA reports | PARTIAL | Organization-wide risk register, owners, treatment plans and review cadence |
| Incident management | RCA evidence and incident-specific audit artifacts | PARTIAL | Formal incident policy, severity model, communications and retained incident records |
| Business continuity | Technical recovery/reset evidence exists | PARTIAL | BCP/DR scope, RTO/RPO, exercises and management-approved results |
| Information security governance | Technical integrity controls and secret separation patterns exist | PARTIAL | ISMS scope, policy set, asset inventory, risk methodology, Statement of Applicability and management approvals |
| Identity/access management | Repository permissions and secret-backed CI controls are visible | PARTIAL | Access-control policy, joiner/mover/leaver records, periodic access reviews |
| Supplier/provider governance | Multi-provider controls and provider admission logic exist | PARTIAL | Supplier inventory, due diligence, contractual/security requirements, periodic reviews |
| Logging/monitoring | Run logs, evidence artifacts and deterministic audit outputs | EVIDENCE_FOUND | Retention/access policy and security-monitoring operating evidence |
| AI governance | Provider controls, evaluator separation and evidence-aware review exist | PARTIAL | AI policy, AI system inventory, risk classification, impact assessment, human oversight and lifecycle records |
| Service management | CI, release and runtime evidence exists | PARTIAL | Service catalog, incident/request/change/problem processes, SLA/SLO ownership and continual-improvement records |
| Privacy governance | No complete privacy management dossier established in this repo | NEEDS_ORG_EVIDENCE | Data inventory, lawful-basis map, retention/deletion, DSR process, processor register, privacy risk assessment |
| Quality management | Extensive technical QA and audit gates | PARTIAL | QMS scope, quality policy/objectives, process owners, nonconformity/CAPA, internal audit and management review |
| Product quality | Deterministic audits, regression suites, performance/evaluator checks | PARTIAL | ISO/IEC 25010 metric catalogue, acceptance thresholds and independent assessment methodology |
| Secure SDLC | Tests, pinned dependencies, provenance and fail-closed gates | PARTIAL | Documented SDLC, threat/risk reviews, vulnerability handling, dependency policy and evidence of periodic review |
| CMMI readiness | Repeatable technical workflows and RCA artifacts | PARTIAL | Organizational process definitions, measurement repository, governance and appraisal-specific objective evidence |
| SOC 2 readiness | Security, integrity and availability-related technical evidence exists | PARTIAL | Formal control descriptions, control owners, operating period evidence and independent CPA attestation |
| OSWorld full benchmark | Focal 061 official score 1.0 plus world-audit evidence | PARTIAL | Full current benchmark under maintainer-accepted V2.1 verification process |
| Worldwide Top-3 claim | No independent full-benchmark placement yet | EXTERNAL_REQUIRED | Comparable full benchmark/publication establishing position |

## Priority closure order

1. Define certification scope and legal/organizational boundary.
2. Establish the integrated policy set: quality, security, AI, privacy, service management, continuity and supplier governance.
3. Build the unified risk register and control ownership matrix.
4. Create evidence-retention and chain-of-custody index linking policies to technical artifacts.
5. Produce internal-audit and management-review records only from real reviews; do not fabricate historical records.
6. Complete external readiness reviews.
7. Engage accredited/authorized external bodies only with explicit commercial approval.
8. Complete OSWorld V2.1 Verified process separately from ISO/CMMI/SOC 2.

## Integrity rule

No gap is marked closed because a document merely exists. Closure requires evidence that the control is implemented and operating for the relevant period. External certifications, attestations, appraisals and leaderboard claims remain external until issued or published by the responsible third party.
