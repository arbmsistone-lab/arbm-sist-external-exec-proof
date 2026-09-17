# ARBM SIST Integrated Risk Register - DRAFT

Status: DRAFT - NOT YET MANAGEMENT APPROVED
Prepared: 2026-09-17

This is a readiness register. Ratings are provisional and must be reviewed by management and control owners before they become operating risk decisions.

Scale:
- Likelihood: 1 (rare) to 5 (very likely)
- Impact: 1 (low) to 5 (critical)
- Inherent score = likelihood x impact
- Residual score must only be assigned after implemented controls and evidence are reviewed.

| ID | Risk | Domain | Likelihood | Impact | Inherent | Existing evidence / control | Current state | Required treatment / evidence |
|---|---|---:|---:|---:|---:|---|---|---|
| R01 | Benchmark result is misrepresented as broader than the tested scope | Quality / market claims | 3 | 5 | 15 | Exact SHA/run/artifact binding; focal-vs-full distinction | PARTIAL | Maintain publication gate; external verified result required for ranking claim |
| R02 | Official evaluator or task integrity is altered | Benchmark integrity | 2 | 5 | 10 | Pre/post evaluator integrity checks; official pins; fail-closed gates | CONTROL_EVIDENCE_FOUND | Add V2.1 pin verifier execution evidence before full run |
| R03 | Stale or mismatched evidence is consumed | Provenance | 2 | 5 | 10 | Stale-evidence purge; approved manifest SHA; candidate SHA verification | CONTROL_EVIDENCE_FOUND | Consolidate chain-of-custody index and retention procedure |
| R04 | Paid fallback occurs under ZERO_SPEND HARD | Financial / execution | 2 | 4 | 8 | ZERO_SPEND_MODE=HARD; paid fallback prohibited | CONTROL_EVIDENCE_FOUND | Formal exception/authorization procedure; retain billing/provider evidence if needed |
| R05 | Heavy workloads execute locally despite policy | Operations | 2 | 4 | 8 | GitHub-hosted/KVM proof; heavy_local=0 evidence | CONTROL_EVIDENCE_FOUND | Formal remote-execution policy and exception process |
| R06 | Secrets or credentials are exposed through source, logs or evidence | Security | 3 | 5 | 15 | Secret-backed CI and credential separation patterns | PARTIAL | Secrets inventory, scanning, access review, rotation and incident procedure |
| R07 | Unauthorized source or release change reaches an evaluated state | Change management | 3 | 5 | 15 | Git SHA lineage; pinned workflows | PARTIAL | Formal approvals, branch/release control, reviewer requirements, rollback evidence |
| R08 | Dependency/supply-chain compromise affects runtime or evidence | Security / supplier | 3 | 5 | 15 | Several dependencies/actions pinned to exact versions/digests | PARTIAL | Supplier inventory, dependency policy, vulnerability review, SBOM/attestation strategy |
| R09 | AI provider/model behavior changes materially without controlled revalidation | AI governance | 4 | 4 | 16 | Provider admission/failover logic and version-sensitive evidence | PARTIAL | AI inventory, version-change triggers, risk reassessment and revalidation criteria |
| R10 | AI-generated action exceeds intended authority or safety boundary | AI governance | 3 | 5 | 15 | Fail-closed gates and constrained benchmark execution | PARTIAL | Intended/prohibited use policy, human oversight rules, high-impact action controls |
| R11 | Service outage or provider failure disrupts critical operation | Continuity | 3 | 4 | 12 | Failover/recovery-related technical evidence exists | PARTIAL | BCP/DR scope, RTO/RPO, exercises, supplier continuity requirements |
| R12 | Incident is detected but not consistently triaged, communicated or closed | Incident management | 3 | 4 | 12 | RCA artifacts and technical audit history | PARTIAL | Severity model, response roles, communications, closure/CAPA records |
| R13 | Personal data is processed without complete inventory, retention or role clarity | Privacy | 3 | 5 | 15 | No complete PIMS dossier yet | OPEN | Data/process inventory, controller/processor mapping, retention, DSR and privacy-risk process |
| R14 | Supplier/provider is used without documented due diligence | Supplier governance | 4 | 4 | 16 | Technical provider admission logic exists | PARTIAL | Supplier register, due diligence, contractual requirements, periodic review |
| R15 | Access remains after role or need changes | IAM | 3 | 5 | 15 | Repository/service permissions exist but org process incomplete | PARTIAL | Joiner/mover/leaver process and periodic access recertification |
| R16 | Logs/evidence expire before external audit | Evidence retention | 3 | 4 | 12 | GitHub artifacts have explicit retention windows | PARTIAL | Retention schedule; export/preserve critical evidence and hashes before expiry |
| R17 | Product-quality claim is based only on internal tests | Product quality | 4 | 4 | 16 | Internal deterministic audits are extensive | PARTIAL | Independent ISO/IEC 25010-based assessment/benchmark; SQS/SIG outreach in progress |
| R18 | Management-system documents exist but controls are not operating | Certification | 4 | 5 | 20 | Program explicitly distinguishes documents from evidence | OPEN | Implement controls, accumulate operating evidence, internal audit, management review |
| R19 | Full OSWorld V2.1 run starts before release/website/provider readiness | Benchmark execution | 3 | 5 | 15 | `full_run_authorized=false`; V2.1 pins documented | CONTROL_DESIGN_FOUND | Require all readiness gates and explicit authorization before full run |
| R20 | Upstream OSWorld limitation is incorrectly attributed to ARBM SIST | Benchmark interpretation | 2 | 4 | 8 | Upstream limitations recorded separately | CONTROL_DESIGN_FOUND | Preserve upstream release notes in external report and claim review |

## Initial priority risks

Prioritize formal treatment of R18, R09, R14, R06, R07, R13, R17 and R19 because their inherent scores or certification impact are highest.

## Closure rule

A risk is not considered treated merely because this register contains a proposed control. Residual risk may only be recorded after implementation evidence is reviewed by the assigned owner and, where applicable, tested by internal or external audit.

`RISK_REGISTER_STATUS = DRAFT_PENDING_OWNER_REVIEW`
