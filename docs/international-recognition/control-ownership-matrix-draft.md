# ARBM SIST Control Ownership Matrix - DRAFT

Status: DRAFT - OWNERS NOT YET FORMALLY APPOINTED
Prepared: 2026-09-17

This matrix defines roles, not named individuals. Formal appointment and acceptance of responsibility are required before this becomes operating evidence.

| Control area | Accountable role | Responsible role | Evidence owner | Review cadence | Status |
|---|---|---|---|---|---|
| Integrated management system | Executive Management | Management System Lead | Management System Lead | Quarterly | TO_ASSIGN |
| Quality objectives / QMS | Executive Management | Quality Lead | Quality Lead | Quarterly | TO_ASSIGN |
| Information security / ISMS | Executive Management | Security Lead | Security Lead | Monthly / quarterly | TO_ASSIGN |
| AI governance / AIMS | Executive Management | AI Governance Lead | AI Governance Lead | Monthly / material change | TO_ASSIGN |
| Privacy / PIMS | Executive Management | Privacy Lead | Privacy Lead | Quarterly / material change | TO_ASSIGN |
| IT service management | Executive Management | Service Management Lead | Service Management Lead | Monthly | TO_ASSIGN |
| Software/product quality | Product Management | Engineering / QA Lead | QA Lead | Per release / quarterly | TO_ASSIGN |
| Secure SDLC | Engineering Management | Engineering Lead | Engineering Lead | Per release | TO_ASSIGN |
| Change / release management | Engineering Management | Release Owner | Release Owner | Per change/release | TO_ASSIGN |
| Benchmark integrity | Engineering Management | Benchmark Integrity Owner | Benchmark Integrity Owner | Per benchmark run | TO_ASSIGN |
| Provenance / evidence custody | Executive Management | Evidence Custodian | Evidence Custodian | Per evidence event / monthly | TO_ASSIGN |
| Risk management | Executive Management | Risk Coordinator | Risk Coordinator | Monthly / quarterly | TO_ASSIGN |
| Incident response | Executive Management | Incident Commander | Incident Coordinator | Per incident / quarterly review | TO_ASSIGN |
| Business continuity / disaster recovery | Executive Management | Continuity Lead | Continuity Lead | Semiannual / annual exercise | TO_ASSIGN |
| Access management | Security Lead | Access Administrator | Security Lead | Monthly / quarterly review | TO_ASSIGN |
| Secrets / credentials | Security Lead | Platform Owner | Security Lead | Monthly / rotation event | TO_ASSIGN |
| Supplier/provider governance | Executive Management | Supplier Owner | Supplier Owner | Onboarding / annual / material change | TO_ASSIGN |
| Vulnerability/dependency management | Security Lead | Engineering Lead | Security Lead | Per release / monthly | TO_ASSIGN |
| Logging / monitoring | Service Management Lead | Platform Owner | Platform Owner | Continuous / monthly review | TO_ASSIGN |
| Data retention / deletion | Privacy Lead | Data/Platform Owner | Privacy Lead | Quarterly | TO_ASSIGN |
| Internal audit | Executive Management | Independent Internal Auditor | Internal Audit Lead | At least annual / before external certification | TO_ASSIGN |
| Management review | Executive Management | Management System Lead | Management System Lead | At least annual / before certification as needed | TO_ASSIGN |
| Corrective action / CAPA | Executive Management | Relevant Process Owner | Quality Lead | Per finding | TO_ASSIGN |
| External certification liaison | Executive Management | Certification Coordinator | Certification Coordinator | As needed | TO_ASSIGN |

## Segregation principles

- The person reviewing benchmark/evaluator integrity should not approve a change that alters evaluator semantics without independent review.
- Internal auditors should not audit their own work where independence can reasonably be achieved.
- High-impact AI and security risk acceptance should be approved by the accountable management role, not only by the implementer.
- Evidence custody must preserve source/run/SHA/hash references and distinguish raw evidence from interpretation.

## Formalization gate

Before Stage 1 or equivalent external readiness review:

1. formally appoint each applicable role;
2. record acceptance of responsibility;
3. define deputies/coverage for critical roles;
4. verify conflicts of interest and segregation needs;
5. retain dated approval evidence.

`CONTROL_OWNERSHIP_STATUS = DRAFT_TO_ASSIGN`
