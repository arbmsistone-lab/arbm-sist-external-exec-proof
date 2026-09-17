# Proposed Integrated Certification / Assurance Scope

Status: WORKING SCOPE FOR READINESS REVIEW
Date: 2026-09-17

This document defines the proposed boundary for external readiness discussions. It is not itself a certificate, attestation, appraisal or legal scope statement.

## Organization / product boundary

Primary subject: `ARBM SIST`

Proposed scope statement:

> Design, development, maintenance, secure operation and continuous improvement of the ARBM SIST software/AI orchestration platform and the supporting processes used to manage quality, information security, AI systems, IT services, privacy, software delivery, incident response, continuity and third-party technology providers.

## In-scope process families

- Product and software lifecycle governance
- Requirements and change management
- Source control and release provenance
- CI/CD and remote execution governance
- Quality assurance and regression testing
- Security engineering and vulnerability handling
- Identity/access and secret-management processes relevant to the platform
- Incident response and root-cause analysis
- Business continuity and technical recovery
- AI/provider selection, admission, failover and governance
- Official evaluator separation and benchmark integrity controls
- Third-party/supplier technology governance
- Service management and operational monitoring
- Privacy/data handling applicable to platform operation
- Risk management and treatment
- Internal audit, corrective action and management review once operating
- Evidence retention and chain of custody

## Technical execution boundary

The existing reproducible technical anchor is:

`73772dbe40650d2e4561693db00ade48e3134ac1`

Technical evidence may reference earlier immutable runs/SHAs where explicitly bound and verified by the current audit chain. Historical evidence remains tied to its original version and must not be presented as if produced under a later release.

## Intended framework mapping

### ISO 9001

Focus: integrated quality-management processes, objectives, process ownership, evidence-based improvement, nonconformity/corrective action, internal audit and management review.

### ISO/IEC 27001

Focus: information-security management system boundaries, risk assessment/treatment, security controls, asset/access/supplier/incident/continuity governance and evidence of operation.

### ISO/IEC 42001

Focus: AI management-system governance, AI inventory, roles, lifecycle controls, risk/impact assessment, provider/model governance, human oversight, monitoring and improvement.

### ISO/IEC 20000-1

Focus: service-management system, service catalogue, service-level governance, incident/problem/change/release/continuity processes and continual improvement.

### ISO/IEC 27701

Focus: privacy information management, processing/data inventory, roles, privacy risk, lifecycle/retention, data-subject processes and processor/controller governance as applicable.

### ISO/IEC 25010

Use as a product-quality assessment model rather than representing it as a management-system certification. Define measurable product-quality characteristics and independent test evidence.

### CMMI

Use for process/maturity appraisal readiness through an authorized appraisal path. No `CMMI certified` wording; only an issued appraisal result may support `appraised at` terminology.

### SOC 2

Use for independent examination of applicable Trust Services Criteria over the defined system and operating period. Readiness documentation is not a SOC 2 report.

### OSWorld V2.1 Verified

Separate benchmark-recognition track. Full current benchmark and maintainer-accepted verification are required before any comparable leaderboard/ranking claim.

## Explicit exclusions from current claim set

Until separately evidenced, the following are excluded from any current certification or market claim:

- worldwide Top-3 placement;
- full OSWorld V2.1 score;
- ISO certificate issuance;
- SOC 2 Type I or Type II report;
- CMMI appraisal result;
- independent ISO/IEC 25010 conformity/quality rating;
- certifications for unrelated ARBM ONE or ZEVANORY operational scopes unless explicitly added by the external body and evidence package.

## Readiness principles

- No fabricated historical operating evidence.
- No backdated approvals.
- No policy document alone closes an operating control.
- External-body scope takes precedence once formally agreed.
- Any paid engagement requires separate explicit owner authorization.
- Engineering/evaluation remains ZERO_SPEND HARD unless separately authorized for a specific external engagement.
- Heavy local remains 0.
- Benchmark evaluator integrity remains fail-closed.

## Scope readiness state

`PROPOSED_INTEGRATED_SCOPE = DOCUMENTED`

`EXTERNAL_SCOPE_APPROVAL = PENDING`
