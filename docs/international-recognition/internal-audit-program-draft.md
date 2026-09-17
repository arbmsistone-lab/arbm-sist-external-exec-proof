# ARBM SIST Internal Audit Program - DRAFT

Status: DRAFT - NO AUDIT YET PERFORMED
Prepared: 2026-09-17

This document defines the future internal-audit program. It is not an audit report and does not create historical operating evidence.

## Audit objective

Evaluate whether the integrated management system is suitably designed, implemented and operating for the agreed scope before external certification/attestation/appraisal.

## Audit criteria

Use the applicable requirements and control objectives from:
- ISO 9001:2026
- ISO/IEC 27001:2022
- ISO/IEC 42001:2023
- ISO/IEC 20000-1:2018
- ISO/IEC 27701:2025
- ISO/IEC 25010:2023 as a product-quality assessment model
- applicable SOC 2 Trust Services Criteria for the defined system
- applicable CMMI appraisal requirements/process areas for the selected target
- OSWorld V2.1 public verification guidance for benchmark claims
- ARBM SIST internal policies, procedures, risk treatment and technical evidence requirements

## Audit principles

- Audit evidence must be sampled from real records and operating controls.
- Documentation alone must not be treated as proof of implementation.
- No backdated approvals or fabricated records.
- Findings must identify criterion, objective evidence, condition, risk and required action.
- Technical evidence must preserve exact source/run/SHA/hash references.
- External-only claims must remain open until independently issued/published.

## Audit coverage

### Audit A - Governance and scope

Verify:
- defined organizational/system boundary;
- policy approval;
- objectives;
- assigned control owners;
- risk methodology/register;
- legal/contractual requirement tracking;
- management review readiness.

### Audit B - Secure engineering and change management

Verify:
- secure SDLC;
- source/release controls;
- approvals and traceability;
- dependency/vulnerability governance;
- secrets handling;
- rollback/recovery evidence;
- evidence provenance.

### Audit C - Information security and access

Verify:
- asset/information inventory;
- access control;
- periodic access review;
- incident response;
- logging/monitoring;
- supplier security;
- continuity and recovery.

### Audit D - AI governance

Verify:
- AI inventory;
- intended/prohibited uses;
- risk/impact assessments;
- provider/model admission;
- version/change triggers;
- human oversight;
- model/provider monitoring;
- evaluator independence for benchmark activities.

### Audit E - Service management

Verify:
- service catalogue;
- service ownership;
- incidents/problems/changes/releases;
- service-level objectives;
- continuity/capacity/supplier management;
- continual improvement.

### Audit F - Privacy

Verify:
- processing/data inventory;
- controller/processor role mapping;
- minimization and retention;
- data-subject request handling where applicable;
- privacy risk assessment;
- processor/subprocessor governance;
- privacy incident handling.

### Audit G - Product quality and external claims

Verify:
- ISO/IEC 25010 metric catalogue;
- objective acceptance thresholds;
- internal vs external evidence separation;
- independent assessment status;
- OSWorld release/version integrity;
- all public quality/ranking claims against supporting evidence.

## Finding classification

- `MAJOR`: systemic absence/failure that materially affects conformity or claim integrity.
- `MINOR`: isolated lapse that does not indicate systemic failure but requires correction.
- `OBSERVATION`: improvement opportunity or emerging risk without a current nonconformity.
- `PASS`: sampled evidence supports the criterion for the period reviewed.

## Evidence record template

For every sampled control record:
- audit area;
- criterion/reference;
- sampled evidence identifier;
- source location;
- date/time;
- owner;
- auditor;
- finding classification;
- exact finding statement;
- corrective-action owner;
- due date;
- closure evidence;
- closure reviewer/date.

## Readiness prerequisites before first internal audit

The first internal audit must not be marked complete until:
1. policy is formally approved;
2. control owners are assigned;
3. risk register is reviewed and treatment decisions recorded;
4. core procedures are effective;
5. enough real operating evidence exists to sample;
6. auditor independence is documented.

## External certification gate

External Stage 1/readiness may begin before every control has a long operating history if the external body permits it, but the organization must disclose evidence maturity accurately. Stage 2, SOC 2 Type II or equivalent operating-effectiveness claims require the evidence period expected by the relevant auditor/body.

`INTERNAL_AUDIT_PROGRAM = DRAFT`
`INTERNAL_AUDIT_COMPLETED = FALSE`
