# ARBM SIST Integrated Risk Register

Status: INITIAL REGISTER ACTIVE
Effective date: 2026-09-17
Approved authority: Owner / Executive Management

Scale:
- Likelihood: 1 (rare) to 5 (very likely)
- Impact: 1 (low) to 5 (critical)
- Inherent score = likelihood x impact
- Residual score remains intentionally unset until implemented controls are evidenced and reviewed.

| ID | Risk | Domain | Likelihood | Impact | Inherent | Existing evidence / control | Current state | Management decision / required treatment |
|---|---|---:|---:|---:|---:|---|---|---|
| R01 | Benchmark result is misrepresented as broader than the tested scope | Quality / market claims | 3 | 5 | 15 | Exact SHA/run/artifact binding; focal-vs-full distinction | PARTIAL | TREAT: keep publication gate; independent verified result required for ranking claim |
| R02 | Official evaluator or task integrity is altered | Benchmark integrity | 2 | 5 | 10 | Pre/post evaluator integrity checks; official pins; fail-closed gates | CONTROL_EVIDENCE_FOUND | TREAT: require V2.1 pin-verifier evidence before any full run |
| R03 | Stale or mismatched evidence is consumed | Provenance | 2 | 5 | 10 | Stale-evidence purge; approved manifest SHA; candidate SHA verification | CONTROL_EVIDENCE_FOUND | TREAT: preserve chain-of-custody index and retention procedure |
| R04 | Paid fallback occurs under ZERO_SPEND HARD | Financial / execution | 2 | 4 | 8 | ZERO_SPEND_MODE=HARD; paid fallback prohibited | CONTROL_EVIDENCE_FOUND | TREAT: explicit authorization required for any paid exception; none authorized |
| R05 | Heavy workloads execute locally despite policy | Operations | 2 | 4 | 8 | GitHub-hosted/KVM proof; heavy_local=0 evidence | CONTROL_EVIDENCE_FOUND | TREAT: remote-only heavy execution; local heavy work prohibited |
| R06 | Secrets or credentials are exposed through source, logs or evidence | Security | 3 | 5 | 15 | Secret-backed CI and credential separation patterns | PARTIAL | TREAT_PRIORITY: secrets inventory, scan, access review, rotation/incident procedure |
| R07 | Unauthorized source or release change reaches an evaluated state | Change management | 3 | 5 | 15 | Git SHA lineage; pinned workflows | PARTIAL | TREAT_PRIORITY: formal approval/review gate, release traceability and rollback evidence |
| R08 | Dependency/supply-chain compromise affects runtime or evidence | Security / supplier | 3 | 5 | 15 | Several dependencies/actions pinned to exact versions/digests | PARTIAL | TREAT: supplier/dependency inventory, vulnerability review and SBOM/attestation strategy |
| R09 | AI provider/model behavior changes materially without controlled revalidation | AI governance | 4 | 4 | 16 | Provider admission/failover logic and version-sensitive evidence | PARTIAL | TREAT_PRIORITY: AI inventory, version-change triggers, reassessment and revalidation criteria |
| R10 | AI-generated action exceeds intended authority or safety boundary | AI governance | 3 | 5 | 15 | Fail-closed gates and constrained benchmark execution | PARTIAL | TREAT: intended/prohibited uses, human oversight and high-impact action controls |
| R11 | Service outage or provider failure disrupts critical operation | Continuity | 3 | 4 | 12 | Failover/recovery-related technical evidence exists | PARTIAL | TREAT: define BCP/DR scope, RTO/RPO, exercises and supplier continuity requirements |
| R12 | Incident is detected but not consistently triaged, communicated or closed | Incident management | 3 | 4 | 12 | RCA artifacts and technical audit history | PARTIAL | TREAT: severity model, roles, communications, closure/CAPA records |
| R13 | Personal data is processed without complete inventory, retention or role clarity | Privacy | 3 | 5 | 15 | No complete PIMS dossier yet | OPEN | TREAT_PRIORITY: data/process inventory, role mapping, retention, DSR and privacy-risk process |
| R14 | Supplier/provider is used without documented due diligence | Supplier governance | 4 | 4 | 16 | Technical provider admission logic exists | PARTIAL | TREAT_PRIORITY: supplier register, due diligence, requirements and periodic review |
| R15 | Access remains after role or need changes | IAM | 3 | 5 | 15 | Repository/service permissions exist but org process incomplete | PARTIAL | TREAT: joiner/mover/leaver process and periodic access recertification |
| R16 | Logs/evidence expire before external audit | Evidence retention | 3 | 4 | 12 | GitHub artifacts have explicit retention windows | PARTIAL | TREAT: retention schedule and preservation of critical evidence/hashes before expiry |
| R17 | Product-quality claim is based only on internal tests | Product quality | 4 | 4 | 16 | Internal deterministic audits are extensive | PARTIAL | TREAT_PRIORITY: independent ISO/IEC 25010 assessment/benchmark; SQS/SIG outreach active |
| R18 | Management-system documents exist but controls are not operating | Certification | 4 | 5 | 20 | Operating-evidence register started 2026-09-17 | TREATMENT_STARTED | TREAT_PRIORITY: accumulate real operating evidence; independent audit after sufficient period |
| R19 | Full OSWorld V2.1 run starts before release/website/provider readiness | Benchmark execution | 3 | 5 | 15 | `full_run_authorized=false`; V2.1 pins documented | CONTROL_DESIGN_FOUND | TREAT_PRIORITY: full run remains blocked until readiness gates pass and explicit authorization is recorded |
| R20 | Upstream OSWorld limitation is incorrectly attributed to ARBM SIST | Benchmark interpretation | 2 | 4 | 8 | Upstream limitations recorded separately | CONTROL_DESIGN_FOUND | TREAT: preserve upstream release limitations in all external reports |

## Priority treatment set approved 2026-09-17

Priority treatment is ACTIVE for R18, R09, R14, R06, R07, R13, R17 and R19.

No risk is marked `ACCEPTED` or given a residual score at this stage. Residual risk requires evidence of control operation and owner review.

## Closure rule

A risk is not considered treated merely because this register contains a proposed control. Residual risk may only be recorded after implementation evidence is reviewed by the assigned owner and, where applicable, tested by internal or external audit.

`RISK_REGISTER_STATUS = INITIAL_ACTIVE_REGISTER`
`RESIDUAL_RATINGS = NOT_YET_ASSIGNED`
